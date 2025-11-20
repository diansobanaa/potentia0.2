import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, TextInput } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import apiClient from '@/src/shared/api/client';

interface Conversation {
  conversation_id: string;
  title: string;
  updated_at?: string;
}


// Module-level cache for conversations
let cachedConversations: Conversation[] | null = null;
let cachedHasMore: boolean | null = null;
let cachedPage: number | null = null;
let hasFetchedConversations = false;

interface ListConversationSidebarProps {
  onCloseSidebar?: () => void;
}

const ListConversationSidebar = React.forwardRef<any, ListConversationSidebarProps>(function ListConversationSidebar(props, ref) {
  const [conversations, setConversations] = useState<Conversation[]>(cachedConversations || []);
  const [loading, setLoading] = useState(!cachedConversations);
  const [expanded, setExpanded] = useState(false);
  const [hasMore, setHasMore] = useState(cachedHasMore !== null ? cachedHasMore : true);
  const [page, setPage] = useState(cachedPage || 1);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const router = useRouter();

  const size = 10;

  const fetchConversations = async (loadMore = false) => {
    // Only allow fetch if not already fetched, unless loading more
    if (!loadMore && hasFetchedConversations && cachedConversations) {
      setConversations(cachedConversations);
      setHasMore(cachedHasMore !== null ? cachedHasMore : true);
      setPage(cachedPage || 1);
      setLoading(false);
      return;
    }
    try {
      const currentPage = loadMore ? page : 1;
      const url = `/api/v1/chat/conversations-list?page=${currentPage}&size=${size}`;
      console.log('Fetching conversations:', url);
      const response = await apiClient.get(url);
      const data = response.data;
      console.log('Conversations response:', data);
      if (data.items && Array.isArray(data.items)) {
        if (loadMore) {
          setConversations(prev => {
            const updated = [...prev, ...data.items];
            cachedConversations = updated;
            return updated;
          });
          setPage(currentPage + 1);
          cachedPage = currentPage + 1;
        } else {
          setConversations(data.items);
          setPage(2);
          cachedConversations = data.items;
          cachedPage = 2;
        }
        setHasMore(currentPage < (data.total_pages || 1));
        cachedHasMore = currentPage < (data.total_pages || 1);
        hasFetchedConversations = true;
      } else {
        console.warn('No items in response');
        setHasMore(false);
        cachedHasMore = false;
      }
    } catch (error) {
      console.error('Error fetching conversations:', error);
      if (!loadMore) {
        setConversations([]);
        cachedConversations = [];
      }
      setHasMore(false);
      cachedHasMore = false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!hasFetchedConversations || !cachedConversations) {
      fetchConversations();
    } else {
      setConversations(cachedConversations);
      setHasMore(cachedHasMore !== null ? cachedHasMore : true);
      setPage(cachedPage || 1);
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleExpand = () => {
    if (expanded) {
      setExpanded(false);
    } else {
      if (hasMore && conversations.length >= size) {
        fetchConversations(true);
      }
      setExpanded(true);
    }
  };

  const visibleConversations = expanded ? conversations : conversations.slice(0, 2);


  if (loading) {
    return (
      <View style={styles.sidebar}>
        <Text style={styles.sidebarTitle}>Percakapan</Text>
        <View style={styles.dropdown}>
          <ActivityIndicator size="small" color="#3b82f6" />
          <Text style={{ color: '#71767b', fontSize: 14, marginTop: 8 }}>Memuat...</Text>
        </View>
      </View>
    );
  }

  if (!loading && conversations.length === 0) {
    return (
      <View style={styles.sidebar}>
        <Text style={styles.sidebarTitle}>Percakapan</Text>
        <View style={styles.dropdown}>
          <Text style={{ color: '#ef4444', fontSize: 14 }}>Tidak ada data percakapan.</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.sidebar} ref={ref}>
      <Text style={styles.sidebarTitle}>Percakapan</Text>
      {/* Add New Chat Button */}
      <TouchableOpacity
        style={styles.addNewChatBtn}
        onPress={() => {
          // Navigate to chat tab with conversation_id = null
          if (router.replace) {
            router.replace('/(app)/(tabs)/chat');
          } else {
            router.push('/(app)/(tabs)/chat');
          }
        }}
        activeOpacity={0.8}
      >
        <Ionicons name="add-circle-outline" size={20} color="#10b981" style={{ marginRight: 8 }} />
        <Text style={{ color: '#10b981', fontWeight: '600', fontSize: 15 }}>Add New Chat</Text>
      </TouchableOpacity>
      <View style={styles.dropdown}>
        {visibleConversations.map(conv => (
          <View key={conv.conversation_id} style={styles.itemRow}>
            {editingId === conv.conversation_id ? (
              <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center' }}>
                <TextInput
                  value={editTitle}
                  onChangeText={setEditTitle}
                  style={[styles.title, styles.editInput]}
                  autoFocus
                  editable={!editLoading}
                  onSubmitEditing={async () => {
                    setEditLoading(true);
                    try {
                      await apiClient.patch(
                        `/api/v1/chat/conversations/${conv.conversation_id}`,
                        { title: editTitle },
                        { headers: { 'Content-Type': 'application/json' } }
                      );
                      setConversations(prev => prev.map(c => c.conversation_id === conv.conversation_id ? { ...c, title: editTitle } : c));
                      setEditingId(null);
                    } catch (e) {
                      alert('Gagal update judul');
                    } finally {
                      setEditLoading(false);
                    }
                  }}
                  onBlur={() => setEditingId(null)}
                  returnKeyType="done"
                />
                {editLoading && <ActivityIndicator size="small" color="#3b82f6" style={{ marginLeft: 8 }} />}
              </View>
            ) : (
              <TouchableOpacity
                style={{ flex: 1 }}
                onPress={() => {
                  router.push(`/(app)/(tabs)/chat/${conv.conversation_id}`);
                  // Try to close sidebar if parent provides a close handler
                  if (props.onCloseSidebar) {
                    props.onCloseSidebar();
                  } else if (ref && typeof ref !== 'function' && ref?.current && typeof ref.current.close === 'function') {
                    ref.current.close();
                  }
                }}
              >
                <Text style={styles.title} numberOfLines={1}>{conv.title}</Text>
              </TouchableOpacity>
            )}
            {editingId !== conv.conversation_id && (
              <TouchableOpacity
                onPress={() => {
                  setEditingId(conv.conversation_id);
                  setEditTitle(conv.title);
                }}
                style={styles.editBtn}
              >
                <Ionicons name="pencil" size={16} color="#3b82f6" />
              </TouchableOpacity>
            )}
          </View>
        ))}
        {conversations.length > 2 && (
          <TouchableOpacity onPress={handleExpand} style={styles.expandBtn}>
            <Text style={styles.expandText}>
              {expanded ? 'Sembunyikan' : hasMore ? 'Lihat semua...' : 'Lihat lebih banyak...'}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
});

export default ListConversationSidebar;

const styles = StyleSheet.create({
    addNewChatBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: 'rgba(255, 255, 255, 0.08)',
      borderRadius: 8,
      paddingVertical: 10,
      paddingHorizontal: 12,
      marginBottom: 10,
      marginTop: 2,
    },
  sidebar: {
    paddingVertical: 16,
    paddingHorizontal: 12,
  },
  sidebarTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  dropdown: {
    backgroundColor: '#23232a',
    borderRadius: 8,
    padding: 8,
  },
  item: {
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#27272a',
  },
  title: {
    color: '#fff',
    fontSize: 16,
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#27272a',
    paddingVertical: 10,
    paddingHorizontal: 5,
    gap: 8,
  },
  editBtn: {
    padding: 4,
    marginLeft: 4,
  },
  editInput: {
    backgroundColor: '#23232a',
    borderRadius: 4,
    paddingHorizontal: 6,
    color: '#fff',
    fontSize: 16,
    flex: 1,
    minWidth: 0,
  },
  subtitle: {
    color: '#71767b',
    fontSize: 12,
    marginTop: 2,
  },
  expandBtn: {
    paddingVertical: 10,
    alignItems: 'center',
  },
  expandText: {
    color: '#3b82f6',
    fontSize: 15,
    fontWeight: '600',
  },
});
