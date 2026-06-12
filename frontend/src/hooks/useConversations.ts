import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import type { ConversationMeta, ConversationData, ConversationTurn } from '../types';
import { parseTurns } from '../utils/format';

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [activeConvData, setActiveConvData] = useState<ConversationData | null>(null);
  const [activeTurn, setActiveTurn] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();

  const searchParams = new URLSearchParams(location.search);
  const idFromUrl = searchParams.get('id');

  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch('/api/conversations');
      if (!res.ok) throw new Error('Failed to load');
      const data: ConversationMeta[] = await res.json();
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const fetchConversationData = useCallback(async (id: string) => {
    setActiveConvId(id);
    setIsLoading(true);
    setActiveTurn(0);
    try {
      const res = await fetch(`/api/conversation/${id}`);
      if (!res.ok) throw new Error('Failed to load conversation');
      const data: ConversationData = await res.json();
      setActiveConvData(data);
    } catch (err) {
      console.error('Failed to load conversation:', err);
      setActiveConvData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const selectConversation = useCallback((id: string) => {
    navigate(`/conversations?id=${id}`);
  }, [navigate]);

  const deselectConversation = useCallback(() => {
    setActiveConvId(null);
    setActiveConvData(null);
    navigate('/conversations');
  }, [navigate]);

  // Handle URL change
  useEffect(() => {
    if (idFromUrl) {
      if (activeConvId !== idFromUrl) {
        fetchConversationData(idFromUrl);
      }
    } else {
      setActiveConvId(null);
      setActiveConvData(null);
    }
  }, [idFromUrl, activeConvId, fetchConversationData]);

  const filteredConversations = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const turns: ConversationTurn[] = activeConvData ? parseTurns(activeConvData.steps) : [];
  const currentTurn = turns[activeTurn] || null;

  return {
    conversations, filteredConversations,
    activeConvId, activeConvData, activeTurn, setActiveTurn,
    searchQuery, setSearchQuery, isLoading,
    selectConversation, deselectConversation, loadConversations,
    turns, currentTurn
  };
}

