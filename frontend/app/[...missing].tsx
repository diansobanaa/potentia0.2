import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter, useSegments } from 'expo-router';

// Catch-all route for unknown paths
export default function NotFoundScreen() {
	const router = useRouter();
	const segments = useSegments();
	return (
		<View style={styles.container}>
			<Text style={styles.code}>404</Text>
			<Text style={styles.title}>Halaman tidak ditemukan</Text>
			<Text style={styles.desc}>Path: /{segments.join('/')}</Text>
			<TouchableOpacity style={styles.button} onPress={() => router.replace('/(app)/(tabs)/home')}>
				<Text style={styles.buttonText}>Kembali ke Home</Text>
			</TouchableOpacity>
		</View>
	);
}

const styles = StyleSheet.create({
	container: { flex: 1, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center', padding: 24 },
	code: { color: '#1d9bf0', fontSize: 48, fontWeight: '800' },
	title: { color: '#fff', fontSize: 20, fontWeight: '700', marginTop: 12 },
	desc: { color: '#71767b', marginTop: 4 },
	button: { marginTop: 20, backgroundColor: '#1d9bf0', paddingHorizontal: 18, paddingVertical: 10, borderRadius: 8 },
	buttonText: { color: '#fff', fontWeight: '600' },
});

