// Relocated: app/(app)/(tabs)/home.tsx
import React, { useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";

export default function HomeScreen() {
  const [activeTab, setActiveTab] = useState<'foryou' | 'following'>('foryou');

  return (
    <View style={styles.container}>
      {/* Top Tabs */}
      <View style={styles.tabsContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'foryou' && styles.tabActive]}
          onPress={() => setActiveTab('foryou')}
        >
          <Text style={[styles.tabText, activeTab === 'foryou' && styles.tabTextActive]}>
            For you
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'following' && styles.tabActive]}
          onPress={() => setActiveTab('following')}
        >
          <Text style={[styles.tabText, activeTab === 'following' && styles.tabTextActive]}>
            Following
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content */}
      <ScrollView contentContainerStyle={styles.content}>
        {activeTab === 'foryou' ? (
          <>
            <Text style={styles.title}>For You Feed</Text>
            <Text style={styles.subtitle}>Konten rekomendasi akan muncul di sini</Text>
          </>
        ) : (
          <>
            <Text style={styles.title}>Following Feed</Text>
            <Text style={styles.subtitle}>Konten dari yang kamu ikuti akan muncul di sini</Text>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: "#000" 
  },
  tabsContainer: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#262626',
    backgroundColor: '#000',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 4,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#3b82f6',
  },
  tabText: {
    color: '#71767b',
    fontSize: 15,
    fontWeight: '700',
  },
  tabTextActive: {
    color: '#fff',
  },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  title: { 
    color: "#fff", 
    fontSize: 20, 
    fontWeight: "700" 
  },
  subtitle: { 
    color: "#71767b", 
    marginTop: 8,
    textAlign: 'center',
  },
});
