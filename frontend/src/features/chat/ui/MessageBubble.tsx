import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import MarkdownDisplay from 'react-native-markdown-display';

const { width: screenWidth } = Dimensions.get('window');

// LEVEL 1: STYLESHEET UNTUK BUBBLE CHAT
const styles = StyleSheet.create({
	bubbleContainer: {
		paddingVertical: 10,
		paddingHorizontal: 15,
		borderRadius: 20,
		marginBottom: 10,
		marginHorizontal: 10,
		maxWidth: screenWidth * 0.97,
	},
	aiBubble: {
		backgroundColor: '#1e1f202c',
		alignSelf: 'flex-start',
		borderBottomLeftRadius: 5,
	},
	userBubble: {
		backgroundColor: '#6e859481',
		alignSelf: 'flex-end',
		borderBottomRightRadius: 5,
	},
});

// LEVEL 2: STYLESHEET UNTUK KONTEN MARKDOWN (Gaya Gemini Dark)
const geminiStylesBase = {
	body: {
		fontSize: 16,
	},
	strong: {
		fontWeight: 'bold',
	},
	link: {
		color: '#8AB4F8',
		textDecorationLine: 'underline',
	},
	heading2: {
		fontSize: 20,
		fontWeight: 'bold',
		borderBottomWidth: 1,
		borderColor: '#555',
		paddingBottom: 5,
		marginTop: 10,
		marginBottom: 5,
	},
	list_item: {
		fontSize: 16,
		marginVertical: 4,
	},
	table: {
		borderColor: '#555',
		borderWidth: 1,
		borderRadius: 8,
		marginTop: 15,
		marginBottom: 15,
		width: screenWidth * 0.75,
		overflow: 'hidden',
	},
	thead: {
		backgroundColor: '#333',
	},
	th: {
		padding: 10,
		fontWeight: 'bold',
		textAlign: 'left',
	},
	tr: {
		borderBottomWidth: 1,
		borderColor: '#555',
	},
	td: {
		padding: 10,
		textAlign: 'left',
	},
};

const geminiStylesAI = StyleSheet.create({
	...geminiStylesBase,
	body: { ...geminiStylesBase.body, color: '#E8EAED' },
	heading2: { ...geminiStylesBase.heading2, color: '#E8EAED' },
	th: { ...geminiStylesBase.th, color: '#E8EAED' },
	td: { ...geminiStylesBase.td, color: '#E8EAED' },
	list_item: { ...geminiStylesBase.list_item, color: '#E8EAED' },
});

const geminiStylesUser = StyleSheet.create({
	...geminiStylesBase,
	body: { ...geminiStylesBase.body, color: '#FFFFFF' },
	heading2: { ...geminiStylesBase.heading2, color: '#FFFFFF' },
	th: { ...geminiStylesBase.th, color: '#FFFFFF' },
	td: { ...geminiStylesBase.td, color: '#FFFFFF' },
	list_item: { ...geminiStylesBase.list_item, color: '#FFFFFF' },
	link: { ...geminiStylesBase.link, color: '#ADD8E6' },
});

type MessageBubbleProps = {
	content: string;
	role: 'user' | 'ai';
};

const MessageBubble: React.FC<MessageBubbleProps> = ({ content, role }) => {
	if (!content) return null;
	const bubbleStyle = role === 'user' ? styles.userBubble : styles.aiBubble;
	const markdownStyle = role === 'user' ? geminiStylesUser : geminiStylesAI;
	return (
		<View style={[styles.bubbleContainer, bubbleStyle]}>
			<MarkdownDisplay style={markdownStyle}>
				{content}
			</MarkdownDisplay>
		</View>
	);
};

export default MessageBubble;
 
