import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface HiTLApprovalCardProps {
  data: any;
  onApprove: () => void;
  onDeny: () => void;
}

export function HiTLApprovalCard({ data, onApprove, onDeny }: HiTLApprovalCardProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Tool Approval Required</Text>
      <Text style={styles.description}>{JSON.stringify(data, null, 2)}</Text>
      <View style={styles.buttons}>
        <TouchableOpacity style={[styles.button, styles.approveButton]} onPress={onApprove}>
          <Text style={styles.buttonText}>Approve</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, styles.denyButton]} onPress={onDeny}>
          <Text style={styles.buttonText}>Deny</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  title: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  description: {
    color: '#ccc',
    fontSize: 14,
    marginBottom: 16,
  },
  buttons: {
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
  },
  approveButton: {
    backgroundColor: '#10b981',
  },
  denyButton: {
    backgroundColor: '#ef4444',
  },
  buttonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
});
