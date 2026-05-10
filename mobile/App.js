import React, { useState } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import TenantScreen from './src/screens/TenantScreen';
import VoterScreen from './src/screens/VoterScreen';

export default function App() {
  const [tenant, setTenant] = useState(null);
  // tenant = { url: string, state: object, appType: string }

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      {tenant
        ? <VoterScreen tenant={tenant} onDisconnect={() => setTenant(null)} />
        : <TenantScreen onConnect={setTenant} />
      }
    </SafeAreaProvider>
  );
}
