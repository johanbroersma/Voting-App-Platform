import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  Image, ActivityIndicator, BackHandler, Alert, Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// ── Theme helpers ────────────────────────────────────────────────────────────

const DEFAULTS = {
  board:  { primary: '#1a3a5c', secondary: '#9e8e85' },
  church: { primary: '#1a2744', secondary: '#b8942a' },
};

function getTheme(state, appType) {
  const def = DEFAULTS[appType] || DEFAULTS.board;
  const primary   = (state?.primaryColor   && /^#[0-9a-fA-F]{6}$/.test(state.primaryColor))   ? state.primaryColor   : def.primary;
  const secondary = (state?.secondaryColor && /^#[0-9a-fA-F]{6}$/.test(state.secondaryColor)) ? state.secondaryColor : def.secondary;
  const orgName   = state?.org || state?.church || (appType === 'board' ? 'Board Voting' : 'Church Voting');
  const denom     = appType === 'church' ? (state?.denomination || '') : '';
  const orgLogo   = state?.orgLogo || null;
  return { primary, secondary, orgName, denom, orgLogo };
}

function logoUri(raw) {
  if (!raw) return null;
  if (raw.startsWith('data:')) return raw;
  return `data:image/png;base64,${raw}`;
}

function hexLuminance(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const toLinear = c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function contrastText(hex) {
  return hexLuminance(hex) > 0.4 ? '#1a1a1a' : '#ffffff';
}

// ── Mode / view logic ────────────────────────────────────────────────────────

function determineMode(state, appType) {
  if (!state) return 'idle';

  if (appType === 'board') {
    if (state.motion?.votingOpen && !state.motion?.complete) return 'motion';
    if (state.election?.votingOpen && !state.election?.complete) return 'election';
    if (state.election?.complete) return 'complete';
    return 'idle';
  }

  // church
  if (state.voting?.votingOpen && !state.voting?.complete) return 'voting';
  const office = state.activeOffice;
  if (office && state[office]?.votingOpen && !state[office]?.complete) return 'election';

  // all-done detection
  const hasElder  = (state.elder?.nominees?.length  || 0) > 0;
  const hasDeacon = (state.deacon?.nominees?.length || 0) > 0;
  const hasVoting = !!state.voting?.question;
  if ((hasElder || hasDeacon || hasVoting)) {
    const elderDone  = !hasElder  || !!state.elder?.complete;
    const deaconDone = !hasDeacon || !!state.deacon?.complete;
    const votingDone = !hasVoting || !!state.voting?.complete;
    if (elderDone && deaconDone && votingDone) return 'complete';
  }
  return 'idle';
}

function hasVotedInMode(state, token, appType) {
  const mode = determineMode(state, appType);

  if (mode === 'election') {
    if (appType === 'board') {
      const round = state.election?.currentRound;
      return (token.usedRounds || []).includes(round);
    }
    const office = state.activeOffice;
    const round  = state[office]?.currentRound;
    return ((token.usedRounds?.[office]) || []).includes(round);
  }
  if (mode === 'motion') {
    return (state.motion?.ballots || []).some(b => b.token === token.code);
  }
  if (mode === 'voting') {
    return !!(token.votedCurrentRound || token.votingVoted);
  }
  return false;
}

function getViewForToken(state, token, appType) {
  const mode = determineMode(state, appType);
  if (mode === 'idle')     return 'idle';
  if (mode === 'complete') return 'complete';
  if (hasVotedInMode(state, token, appType)) return 'done';
  return mode;
}

function getBallotData(state, appType) {
  const mode = determineMode(state, appType);
  if (mode === 'election') {
    if (appType === 'board') {
      return {
        title: state.election?.electionName || 'Election',
        subtitle: null,
        candidates: (state.election?.candidates || []).map(c => c.name),
        votesPerVoter: state.election?.votesPerVoter || 1,
        maxSelections: state.election?.openPositions || state.election?.votesPerVoter || 1,
      };
    }
    const office = state.activeOffice;
    const off    = state[office] || {};
    const label  = office === 'elder' ? 'Elder' : 'Deacon';
    return {
      title: `Election of ${label}s`,
      subtitle: `Select up to ${off.votesPerVoter || 1} candidate${(off.votesPerVoter || 1) > 1 ? 's' : ''}`,
      candidates: (off.candidates || []).map(c => c.name),
      votesPerVoter: off.votesPerVoter || 1,
      maxSelections: off.votesPerVoter || 1,
    };
  }
  if (mode === 'motion') {
    return {
      title: 'Motion',
      subtitle: state.motion?.text || '',
      candidates: state.motion?.options || [],
      votesPerVoter: state.motion?.votesPerVoter || 1,
      maxSelections: state.motion?.votesPerVoter || 1,
    };
  }
  if (mode === 'voting') {
    return {
      title: state.voting?.question || 'Congregational Vote',
      subtitle: null,
      candidates: state.voting?.answers || [],
      votesPerVoter: 1,
      maxSelections: 1,
    };
  }
  return null;
}

// ── Main component ────────────────────────────────────────────────────────────

const POLL_INTERVAL = 3000;

export default function VoterScreen({ tenant, onDisconnect }) {
  const insets = useSafeAreaInsets();
  const { url, appType } = tenant;

  const [appState,    setAppState]    = useState(tenant.state);
  const [view,        setView]        = useState('token');  // token | election | motion | voting | done | idle | complete | error
  const [tokenInput,  setTokenInput]  = useState('');
  const [currentToken,setCurrentToken]= useState(null);
  const [selections,  setSelections]  = useState([]);
  const [submitting,  setSubmitting]  = useState(false);
  const [errorMsg,    setErrorMsg]    = useState('');
  const [doneLabel,   setDoneLabel]   = useState('');

  const pollRef = useRef(null);
  const theme   = getTheme(appState, appType);

  // Back handler (Android)
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (view !== 'token') {
        Alert.alert('Disconnect?', 'Return to the tenant selection screen?', [
          { text: 'Stay', style: 'cancel' },
          { text: 'Disconnect', style: 'destructive', onPress: onDisconnect },
        ]);
        return true;
      }
      onDisconnect();
      return true;
    });
    return () => sub.remove();
  }, [view, onDisconnect]);

  // Polling
  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${url}/api/state`, { cache: 'no-store' });
      if (!res.ok) return;
      const newState = await res.json();
      setAppState(newState);
      return newState;
    } catch { /* ignore network blips */ }
  }, [url]);

  useEffect(() => {
    pollRef.current = setInterval(fetchState, POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, [fetchState]);

  // Re-evaluate view when state changes and token is active
  useEffect(() => {
    if (!currentToken || view === 'token') return;
    // Refresh token data from latest state
    const freshToken = (appState.tokens || []).find(t => t.code === currentToken.code);
    if (!freshToken) return;
    const newView = getViewForToken(appState, freshToken, appType);
    if (newView !== view) {
      setCurrentToken(freshToken);
      setSelections([]);
      setErrorMsg('');
      setView(newView);
    }
  }, [appState]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Token entry ──────────────────────────────────────────────────────────

  async function submitToken() {
    const code = tokenInput.trim().toUpperCase();
    if (!code) { setErrorMsg('Please enter your token code.'); return; }
    setErrorMsg('');
    // Fetch fresh state so tokens added after connect are visible
    const latest = await fetchState() || appState;
    const token = (latest.tokens || []).find(t => t.code === code);
    if (!token) { setErrorMsg('Token not found. Please check the code and try again.'); return; }
    setCurrentToken(token);
    const nextView = getViewForToken(latest, token, appType);
    if (nextView === 'done') {
      const mode = determineMode(latest, appType);
      setDoneLabel(modeDoneLabel(mode, latest, appType));
    }
    setView(nextView);
  }

  function modeDoneLabel(mode, state, at) {
    if (mode === 'election') {
      if (at === 'church') {
        const off = state.activeOffice === 'elder' ? 'Elder' : 'Deacon';
        return `${off} election — Round ${state[state.activeOffice]?.currentRound || '?'}`;
      }
      return `Election — Round ${state.election?.currentRound || '?'}`;
    }
    if (mode === 'motion') return 'Motion vote';
    if (mode === 'voting') return 'Congregational vote';
    return 'Vote';
  }

  // ── Ballot submission ─────────────────────────────────────────────────────

  async function submitBallot() {
    const mode = determineMode(appState, appType);
    if (!selections.length) { setErrorMsg('Please make a selection.'); return; }
    setSubmitting(true);
    setErrorMsg('');

    let endpoint, body;

    if (mode === 'election' && appType === 'board') {
      endpoint = '/api/ballot';
      body = {
        round:      appState.election.currentRound,
        tokenCode:  currentToken.code,
        selections,
      };
    } else if (mode === 'election' && appType === 'church') {
      endpoint = '/api/ballot';
      const office = appState.activeOffice;
      body = {
        office,
        round:     appState[office].currentRound,
        tokenCode: currentToken.code,
        selections,
      };
    } else if (mode === 'motion') {
      endpoint = '/api/motion-ballot';
      body = { tokenCode: currentToken.code, selections };
    } else if (mode === 'voting') {
      endpoint = '/api/voting-ballot';
      body = { tokenCode: currentToken.code, answer: selections[0] };
    } else {
      setSubmitting(false);
      return;
    }

    try {
      const res = await fetch(`${url}${endpoint}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setErrorMsg(data.error || `Error ${res.status}`);
      } else {
        setDoneLabel(modeDoneLabel(mode, appState, appType));
        setSelections([]);
        await fetchState();
        setView('done');
      }
    } catch (e) {
      setErrorMsg(`Network error: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleSelection(name, maxSelections) {
    setSelections(prev => {
      if (prev.includes(name)) return prev.filter(s => s !== name);
      if (prev.length >= maxSelections) {
        if (maxSelections === 1) return [name];
        return prev;
      }
      return [...prev, name];
    });
  }

  // ── Render helpers ────────────────────────────────────────────────────────

  function renderHeader() {
    const logoSrc = logoUri(theme.orgLogo);
    return (
      <View style={[styles.header, { backgroundColor: theme.primary, paddingTop: insets.top + 12 }]}>
        <View style={styles.headerInner}>
          {logoSrc && (
            <Image
              source={{ uri: logoSrc }}
              style={styles.logo}
              resizeMode="contain"
            />
          )}
          <View style={styles.headerText}>
            <Text style={[styles.orgName, { color: contrastText(theme.primary) }]} numberOfLines={1}>
              {theme.orgName}
            </Text>
            {!!theme.denom && (
              <Text style={[styles.orgDenom, { color: contrastText(theme.primary), opacity: 0.75 }]} numberOfLines={1}>
                {theme.denom}
              </Text>
            )}
          </View>
          <TouchableOpacity onPress={onDisconnect} style={styles.disconnectBtn} hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <Text style={[styles.disconnectText, { color: contrastText(theme.primary), opacity: 0.7 }]}>✕</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  function renderTokenView() {
    const hasTokens = (appState.tokens || []).length > 0;

    if (!hasTokens) {
      return (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.card}>
            <Text style={styles.idleTitle}>No Tokens Available</Text>
            <Text style={styles.waitText}>
              Voter tokens have not been set up yet. Please wait — this screen will update automatically.
            </Text>
            <View style={styles.pollingIndicator}>
              <ActivityIndicator size="small" color={theme.primary} />
              <Text style={[styles.pollingText, { color: theme.primary }]}>Checking for tokens</Text>
            </View>
          </View>
        </ScrollView>
      );
    }

    return (
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Enter Your Token</Text>
          <TextInput
            style={styles.tokenInput}
            value={tokenInput}
            onChangeText={t => { setTokenInput(t.toUpperCase()); setErrorMsg(''); }}
            placeholder="e.g.  1234"
            placeholderTextColor="#9ca3af"
            autoCapitalize="characters"
            autoCorrect={false}
            spellCheck={false}
            keyboardType="number-pad"
            returnKeyType="go"
            onSubmitEditing={submitToken}
          />
          {!!errorMsg && <Text style={styles.errorText}>{errorMsg}</Text>}
          <TouchableOpacity
            style={[styles.primaryBtn, { backgroundColor: theme.primary }]}
            onPress={submitToken}
            activeOpacity={0.85}
          >
            <Text style={[styles.primaryBtnText, { color: contrastText(theme.primary) }]}>Continue</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  function renderBallotView() {
    const ballot = getBallotData(appState, appType);
    if (!ballot) return renderIdleView();

    return (
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{ballot.title}</Text>
          {!!ballot.subtitle && (
            <Text style={styles.cardSubtitle}>{ballot.subtitle}</Text>
          )}
          {ballot.maxSelections > 1 && (
            <Text style={styles.selectionHint}>
              Select up to {ballot.maxSelections} — {selections.length} selected
            </Text>
          )}

          <View style={styles.candidateList}>
            {ballot.candidates.map(name => {
              const selected = selections.includes(name);
              return (
                <TouchableOpacity
                  key={name}
                  style={[
                    styles.candidateRow,
                    selected && { backgroundColor: theme.secondary, borderColor: theme.secondary },
                  ]}
                  onPress={() => toggleSelection(name, ballot.maxSelections)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.checkbox, selected && { backgroundColor: theme.primary, borderColor: theme.primary }]}>
                    {selected && <Text style={styles.checkmark}>✓</Text>}
                  </View>
                  <Text style={[styles.candidateName, selected && { color: contrastText(theme.secondary), fontWeight: '600' }]}>
                    {name}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {!!errorMsg && <Text style={styles.errorText}>{errorMsg}</Text>}

          <TouchableOpacity
            style={[
              styles.primaryBtn,
              { backgroundColor: theme.primary },
              (!selections.length || submitting) && styles.primaryBtnDisabled,
            ]}
            onPress={submitBallot}
            disabled={!selections.length || submitting}
            activeOpacity={0.85}
          >
            {submitting
              ? <ActivityIndicator color={contrastText(theme.primary)} />
              : <Text style={[styles.primaryBtnText, { color: contrastText(theme.primary) }]}>Submit Vote</Text>
            }
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  function renderDoneView() {
    const mode = determineMode(appState, appType);
    const isComplete = mode === 'complete';
    return (
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.card}>
          <View style={[styles.doneIcon, { backgroundColor: theme.secondary }]}>
            <Text style={[styles.doneIconText, { color: contrastText(theme.secondary) }]}>✓</Text>
          </View>
          <Text style={styles.cardTitle}>Vote Recorded</Text>
          <Text style={styles.doneSubtitle}>{doneLabel}</Text>
          {isComplete
            ? <Text style={styles.waitText}>All voting is complete. Thank you for participating!</Text>
            : <Text style={styles.waitText}>Waiting for the next round to open…</Text>
          }
          {!isComplete && (
            <View style={styles.pollingIndicator}>
              <ActivityIndicator size="small" color={theme.primary} />
              <Text style={[styles.pollingText, { color: theme.primary }]}>Checking for updates</Text>
            </View>
          )}
        </View>
      </ScrollView>
    );
  }

  function renderIdleView() {
    return (
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.card}>
          <Text style={styles.idleTitle}>No Vote Open</Text>
          <Text style={styles.waitText}>
            There is no active vote at this time. This screen will update automatically when voting opens.
          </Text>
          <View style={styles.pollingIndicator}>
            <ActivityIndicator size="small" color={theme.primary} />
            <Text style={[styles.pollingText, { color: theme.primary }]}>Waiting for voting to open</Text>
          </View>
          <TouchableOpacity
            style={[styles.secondaryBtn, { borderColor: theme.primary }]}
            onPress={() => setView('token')}
            activeOpacity={0.85}
          >
            <Text style={[styles.secondaryBtnText, { color: theme.primary }]}>Change Token</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  function renderCompleteView() {
    return (
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.card}>
          <View style={[styles.doneIcon, { backgroundColor: theme.secondary }]}>
            <Text style={[styles.doneIconText, { color: contrastText(theme.secondary) }]}>✓</Text>
          </View>
          <Text style={styles.cardTitle}>Election Complete</Text>
          <Text style={styles.waitText}>
            All voting has concluded. Thank you for participating!
          </Text>
          <TouchableOpacity
            style={[styles.secondaryBtn, { borderColor: theme.primary }]}
            onPress={() => { setView('token'); setCurrentToken(null); setTokenInput(''); }}
            activeOpacity={0.85}
          >
            <Text style={[styles.secondaryBtnText, { color: theme.primary }]}>Start Over</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  function renderBody() {
    switch (view) {
      case 'token':    return renderTokenView();
      case 'election': return renderBallotView();
      case 'motion':   return renderBallotView();
      case 'voting':   return renderBallotView();
      case 'done':     return renderDoneView();
      case 'idle':     return renderIdleView();
      case 'complete': return renderCompleteView();
      default:         return renderTokenView();
    }
  }

  return (
    <View style={styles.root}>
      {renderHeader()}
      <View style={[styles.body, { paddingBottom: insets.bottom }]}>
        {renderBody()}
      </View>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#f1f5f9',
  },
  header: {
    paddingBottom: 16,
    paddingHorizontal: 20,
  },
  headerInner: {
    flexDirection: 'row',
    alignItems: 'center',
    maxWidth: 560,
    alignSelf: 'center',
    width: '100%',
  },
  logo: {
    width: 44,
    height: 44,
    marginRight: 12,
  },
  headerText: {
    flex: 1,
  },
  orgName: {
    fontSize: 17,
    fontWeight: '700',
  },
  orgDenom: {
    fontSize: 12,
    marginTop: 1,
  },
  disconnectBtn: {
    padding: 4,
  },
  disconnectText: {
    fontSize: 18,
    fontWeight: '600',
  },
  body: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
    paddingTop: 24,
    alignItems: 'center',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 520,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 20,
  },
  noVoteNotice: {
    backgroundColor: '#fef3c7',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  noVoteText: {
    fontSize: 13,
    color: '#92400e',
    textAlign: 'center',
    lineHeight: 18,
  },
  tokenInput: {
    height: 56,
    borderWidth: 1.5,
    borderColor: '#d1d5db',
    borderRadius: 10,
    paddingHorizontal: 16,
    fontSize: 22,
    fontWeight: '700',
    color: '#111827',
    backgroundColor: '#f9fafb',
    textAlign: 'center',
    letterSpacing: 4,
    marginBottom: 16,
  },
  selectionHint: {
    fontSize: 13,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 12,
  },
  candidateList: {
    marginBottom: 16,
    gap: 8,
  },
  candidateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    backgroundColor: '#f9fafb',
    marginBottom: 8,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: '#d1d5db',
    backgroundColor: '#fff',
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkmark: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 16,
  },
  candidateName: {
    fontSize: 16,
    color: '#111827',
    flex: 1,
  },
  primaryBtn: {
    height: 52,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 4,
  },
  primaryBtnDisabled: {
    opacity: 0.45,
  },
  primaryBtnText: {
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  secondaryBtn: {
    height: 48,
    borderRadius: 10,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  secondaryBtnText: {
    fontSize: 15,
    fontWeight: '600',
  },
  errorText: {
    color: '#dc2626',
    fontSize: 13,
    marginBottom: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  doneIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 16,
  },
  doneIconText: {
    fontSize: 30,
    fontWeight: '700',
    lineHeight: 36,
  },
  doneSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 16,
  },
  waitText: {
    fontSize: 15,
    color: '#374151',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 20,
  },
  pollingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 8,
  },
  pollingText: {
    fontSize: 13,
    fontWeight: '500',
  },
  idleTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 12,
  },
});
