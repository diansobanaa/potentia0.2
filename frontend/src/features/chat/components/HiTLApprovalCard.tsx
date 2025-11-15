// src/features/chat/components/HiTLApprovalCard.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Button } from '@components/ui/Button';
import { theme } from '@config/theme';
import type { ToolApprovalRequest } from '@types/chat.types';

interface HiTLApprovalCardProps {
  request: ToolApprovalRequest;
  onApprove: () => void;
  onReject: () => void;
}

export const HiTLApprovalCard: React.FC<HiTLApprovalCardProps> = ({
  request,
  onApprove,
  onReject,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.icon}>🛡️</Text>
        <Text style={styles.title}>Tool Approval Required</Text>
      </View>
      
      <View style={styles.content}>
        <Text style={styles.toolName}>
          Tool: <Text style={styles.toolNameBold}>{request.tool_name}</Text>
        </Text>
        
        {request.reasoning && (
          <Text style={styles.reasoning}>{request.reasoning}</Text>
        )}
        
        {Object.keys(request.args).length > 0 && (
          <View style={styles.argsContainer}>
            <Text style={styles.argsLabel}>Arguments:</Text>
            {Object.entries(request.args).map(([key, value]) => (
              <Text key={key} style={styles.argItem}>
                • {key}: {JSON.stringify(value)}
              </Text>
            ))}
          </View>
        )}
      </View>
      
      <View style={styles.actions}>
        <Button
          onPress={onApprove}
          variant="primary"
          style={styles.approveButton}
        >
          Approve
        </Button>
        <Button
          onPress={onReject}
          variant="danger"
          style={styles.rejectButton}
        >
          Reject
        </Button>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FEF3C7',
    borderLeftWidth: 4,
    borderLeftColor: '#F59E0B',
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginVertical: theme.spacing.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  icon: {
    fontSize: 24,
    marginRight: theme.spacing.xs,
  },
  title: {
    fontSize: theme.fontSize.lg,
    fontWeight: 'bold',
    color: '#92400E',
  },
  content: {
    marginBottom: theme.spacing.md,
  },
  toolName: {
    fontSize: theme.fontSize.md,
    color: '#78350F',
    marginBottom: theme.spacing.xs,
  },
  toolNameBold: {
    fontWeight: 'bold',
  },
  reasoning: {
    fontSize: theme.fontSize.sm,
    color: '#78350F',
    marginBottom: theme.spacing.sm,
    fontStyle: 'italic',
  },
  argsContainer: {
    backgroundColor: '#FFFBEB',
    borderRadius: theme.borderRadius.sm,
    padding: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  argsLabel: {
    fontSize: theme.fontSize.sm,
    fontWeight: '600',
    color: '#78350F',
    marginBottom: theme.spacing.xs,
  },
  argItem: {
    fontSize: theme.fontSize.xs,
    color: '#92400E',
    marginLeft: theme.spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
  },
  approveButton: {
    flex: 1,
  },
  rejectButton: {
    flex: 1,
  },
});
