// src/shared/ui/MarkdownText.tsx


import React from 'react';
import { StyleSheet } from 'react-native';
import Markdown from 'react-native-markdown-display';


interface MarkdownTextProps {
  children: string;
  style?: any;
}

export function MarkdownText({ children, style }: MarkdownTextProps) {
  const mergedStyle = style ? { ...defaultMarkdownStyle, ...style } : defaultMarkdownStyle;
  return (
    <Markdown style={mergedStyle}>
      {children}
    </Markdown>
  );
}

const defaultMarkdownStyle = StyleSheet.create({
  body: {
    color: '#fff',
    fontSize: 16,
    lineHeight: 26,
    fontFamily: 'Inter, System, -apple-system, Roboto, "Segoe UI", Arial',
    letterSpacing: 0.1,
  },
  heading1: {
    fontSize: 22,
    fontWeight: 'bold',
    marginVertical: 10,
    color: '#fff',
    lineHeight: 30,
  },
  heading2: {
    fontSize: 20,
    fontWeight: 'bold',
    marginVertical: 8,
    color: '#fff',
    lineHeight: 28,
  },
  heading3: {
    fontSize: 18,
    fontWeight: 'bold',
    marginVertical: 6,
    color: '#fff',
    lineHeight: 26,
  },
  paragraph: {
    marginVertical: 6,
    color: '#fff',
    lineHeight: 26,
  },
  link: {
    color: '#4fa3ff',
    textDecorationLine: 'underline',
    fontWeight: '500',
  },
  code_inline: {
    backgroundColor: '#23272f',
    fontFamily: 'Menlo, monospace',
    fontSize: 15,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 5,
    color: '#ffb86c',
  },
  code_block: {
    backgroundColor: '#23272f',
    fontFamily: 'Menlo, monospace',
    fontSize: 15,
    padding: 12,
    borderRadius: 8,
    color: '#fff',
    marginVertical: 10,
    lineHeight: 22,
  },
  list_item: {
    marginVertical: 4,
    color: '#fff',
    lineHeight: 26,
  },
});



