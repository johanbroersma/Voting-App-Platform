import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { buildTenantUrl } from '../config';

const STORAGE_KEY = 'lastTenantCode';

function detectAppType(state) {
  if (state.appType) return state.appType;
  if ('church' in state || 'elder' in state || 'deacon' in state || 'activeOffice' in state) return 'church';
  if ('org' in state || 'election' in state || 'motion' in state) return 'board';
  return null;
}

export default function TenantScreen({ onConnect }) {
  const insets = useSafeAreaInsets();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then(saved => {
      if (saved) setCode(saved);
    });
  }, []);

  async function connect() {
    const trimmed = code.trim();
    if (!trimmed) { setError('Please enter a tenant code or URL.'); return; }
    setError('');
    setLoading(true);
    try {
      const url = buildTenantUrl(trimmed);
      const res = await fetch(`${url}/api/state`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const state = await res.json();
      const appType = detectAppType(state);
      if (!appType) {
        // Store anyway — app type will be detected once admin configures election
        await AsyncStorage.setItem(STORAGE_KEY, trimmed);
        onConnect({ url, state, appType: 'board' });
        return;
      }
      await AsyncStorage.setItem(STORAGE_KEY, trimmed);
      onConnect({ url, state, appType });
    } catch (e) {
      setError(`Could not connect: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: '#1a3a5c' }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={[styles.container, { paddingTop: insets.top + 40, paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.inner}>
          <Text style={styles.appTitle}>Voting App</Text>
          <Text style={styles.tagline}>Enter your organisation's voting code to get started</Text>

          <View style={styles.card}>
            <Text style={styles.label}>Tenant Code</Text>
            <TextInput
              style={styles.input}
              value={code}
              onChangeText={t => { setCode(t); setError(''); }}
              placeholder="e.g. gracebc  or  http://192.168.1.5:8080"
              placeholderTextColor="#9ca3af"
              autoCapitalize="none"
              autoCorrect={false}
              spellCheck={false}
              returnKeyType="go"
              onSubmitEditing={connect}
            />
            {!!error && <Text style={styles.errorText}>{error}</Text>}

            <TouchableOpacity
              style={[styles.connectBtn, loading && styles.connectBtnDisabled]}
              onPress={connect}
              disabled={loading}
              activeOpacity={0.85}
            >
              {loading
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.connectBtnText}>Connect</Text>
              }
            </TouchableOpacity>
          </View>

          <Text style={styles.hint}>
            Your voting code is provided by your organisation's election coordinator.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  inner: {
    width: '100%',
    maxWidth: 480,
    alignSelf: 'center',
  },
  appTitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 8,
  },
  tagline: {
    fontSize: 15,
    color: '#cbd5e1',
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 22,
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    height: 48,
    borderWidth: 1.5,
    borderColor: '#d1d5db',
    borderRadius: 10,
    paddingHorizontal: 14,
    fontSize: 16,
    color: '#111827',
    backgroundColor: '#f9fafb',
    marginBottom: 16,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 13,
    marginBottom: 12,
    lineHeight: 18,
  },
  connectBtn: {
    height: 50,
    backgroundColor: '#1a3a5c',
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  connectBtnDisabled: {
    opacity: 0.6,
  },
  connectBtnText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  hint: {
    marginTop: 24,
    fontSize: 13,
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: 20,
  },
});
