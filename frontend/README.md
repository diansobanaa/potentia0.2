# Potentia Frontend

React Native + Expo frontend for Potentia AI collaborative canvas platform.

## 🏗️ Architecture

**Feature-Sliced Design** - Modular, scalable architecture:
- ✅ Auth feature with JWT + SecureStorage
- ✅ Chat feature with SSE streaming + Human-in-the-Loop
- ✅ Zustand for state management
- ✅ Axios for API calls
- ✅ EventSource polyfill for SSE

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Expo Go app (for mobile testing)

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Update API URL in .env to your local IP
# Example: EXPO_PUBLIC_API_URL=http://192.168.1.100:8000
```

### Development

```bash
# Start Expo dev server
npm start

# Run on specific platform
npm run android
npm run ios
npm run web
```

## 🧹 Commit & Repository Hygiene

Tujuan: hanya commit kode sumber yang kita tulis, hindari artefak build, dependency, atau rahasia.

### Commit yang WAJIB disertakan
- `app/` (routing & screens)
- `src/` (features, components, services, types, config)
- `package.json` dan `package-lock.json` (lock file penting untuk reproduksi)
- Konfigurasi build (misal `babel.config.js`, `tsconfig.json`, `app.json`)
- Dokumen: `README.md`, `ARCHITECTURE.md`, dsb.

### Jangan di-commit (sudah di-ignore `.gitignore`)
- `.env` / semua file berisi secret
- `node_modules/`, `.expo/`, `dist/`, `web-build/`
- Cache / artefak: `*.tsbuildinfo`, log (`npm-debug.log`), temp

### Langkah Repro Environment
Gunakan `npm ci` (bukan `npm install`) untuk pemasangan deterministik di CI / server baru:
```bash
npm ci
```

### Checklist sebelum commit
```bash
git status            # pastikan tidak ada .env atau artefak ter-stage
git diff --name-only  # lihat file yang berubah
```

Stage selektif (ketat):
```bash
git add app src package.json package-lock.json babel.config.js tsconfig.json app.json README.md
```
Atau jika yakin `.gitignore` sudah benar:
```bash
git add .
```
Kemudian commit & push:
```bash
git commit -m "feat: canvas real-time + chat fixes"
git push origin main
```

### Snapshot dependency (opsional untuk dokumentasi)
Top-level versi saja:
```bash
npm ls --depth=0 > DEPENDENCIES_TOP_LEVEL.txt
```
Semua dependency (besar):
```bash
npm ls --json > deps-full.json
```

### Pre-commit (opsional)
Tambahkan script lint/format sebelum commit (pakai husky / simple manual):
```bash
npm run lint
npm run typecheck
```

### Menghindari commit rahasia
- Jangan pernah masukkan API key ke code: akses melalui `process.env.EXPO_PUBLIC_*`
- Validasi dengan pencarian cepat:
```bash
grep -R "API_KEY" -n src app || echo "OK"
```

### Recovery kalau terlanjur commit .env
```bash
git rm --cached .env
git commit -m "chore: remove .env from repo"
git push
```
Regenerasi secret (anggap sudah bocor) di provider terkait.

---
Dengan aturan di atas, repo tetap ramping & mudah direproduksi.


### Testing on Device

1. Install Expo Go app on your phone
2. Scan QR code from terminal
3. Ensure phone and dev machine are on same WiFi
4. Update `.env` with your local IP address

## 📁 Project Structure

```
frontend/
├── app/                    # Expo Router (file-based routing)
│   ├── (auth)/            # Auth screens (login, register)
│   ├── (tabs)/            # Main app (home, chat)
│   └── _layout.tsx        # Root layout
│
├── src/
│   ├── features/          # Feature-Sliced Design
│   │   ├── auth/         # Authentication feature
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── store/    # authStore.ts
│   │   ├── chat/         # Chat + HiTL feature
│   │   │   ├── components/
│   │   │   │   ├── HiTLApprovalCard.tsx  # Human-in-the-Loop
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── MessageInput.tsx
│   │   │   ├── hooks/
│   │   │   └── store/    # chatStore.ts
│   │   └── canvas/       # Canvas feature (TODO)
│   │
│   ├── components/       # Global UI components
│   │   └── ui/          # Button, Input, etc.
│   │
│   ├── services/
│   │   ├── api/         # API clients
│   │   │   ├── client.ts      # Axios instance
│   │   │   ├── auth.api.ts
│   │   │   └── chat.api.ts    # SSE streaming
│   │   ├── real-time/   # WebSocket managers
│   │   └── storage/     # SecureStorage
│   │
│   ├── types/           # TypeScript definitions
│   ├── utils/           # Utility functions
│   └── config/          # App configuration
│       ├── env.ts       # Environment vars
│       └── theme.ts     # Design tokens
```

## 🔑 Key Features

### 1. **Human-in-the-Loop (HiTL)**
Critical safety feature for AI tool execution:

```typescript
// Backend sends tool_approval_required event
{
  "type": "tool_approval_required",
  "payload": {
    "tool_name": "delete_canvas",
    "args": { "canvas_id": "123" },
    "reasoning": "User requested deletion"
  }
}

// Frontend shows HiTLApprovalCard
// User clicks Approve/Reject
// Backend continues/stops execution
```

### 2. **SSE Streaming**
Real-time AI responses with token-by-token streaming:

```typescript
// Event types:
- metadata       → conversation_id, message_id
- status         → "Thinking...", "Searching..."
- token_chunk    → Incremental text
- errorStatus    → Fallback errors
- final_state    → Complete message + tokens
```

### 3. **State Management**
Single source of truth with Zustand:

```typescript
// chatStore.ts
const { sendMessage, approvalRequest } = useChatStore();

// All state in store - no component state duplication
```

## 🛠️ Development Workflow

### Adding a New Feature

1. Create feature folder: `src/features/your-feature/`
2. Add components: `components/YourComponent.tsx`
3. Add store: `store/yourFeatureStore.ts`
4. Add API: `src/services/api/your-feature.api.ts`
5. Add types: `src/types/your-feature.types.ts`
6. Create route: `app/your-feature/[id].tsx`

### Path Aliases

```typescript
import { useAuth } from '@features/auth/hooks/useAuth';
import { Button } from '@components/ui';
import { chatApi } from '@services/api/chat.api';
import { ENV } from '@config/env';
```

## 📡 Backend Integration

### Required Backend Endpoints

- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/chat/` - SSE streaming chat
- `POST /api/v1/chat/{id}/actions/approve_tool` - HiTL approve
- `POST /api/v1/chat/{id}/actions/reject_tool` - HiTL reject
- `GET /api/v1/chat/conversations-list` - List conversations
- `GET /api/v1/chat/{id}/messages` - Get messages

### CORS Configuration

Backend must allow your IP:

```python
# backend/app/main.py
allow_origins=[
    "http://localhost:3000",
    "http://192.168.1.100:8081",  # Your IP + Expo port
    "exp://192.168.1.100:8081"    # Expo deep link
]
```

## 🐛 Troubleshooting

### Issue: "Cannot connect to backend"
- ✅ Check `.env` has correct IP address
- ✅ Backend running on `0.0.0.0:8000`
- ✅ Phone/computer on same WiFi
- ✅ Firewall allows port 8000

### Issue: "Module not found @features/..."
- ✅ Run `npm install`
- ✅ Clear cache: `expo start -c`
- ✅ Check `babel.config.js` has module-resolver

### Issue: "EventSource polyfill not working"
- ✅ Install: `npm install event-source-polyfill`
- ✅ Import in API: `import { EventSourcePolyfill } from 'event-source-polyfill'`

## 📦 Build & Deploy

### Web (PWA)

```bash
npm run web
# or
expo build:web
```

### Android APK

```bash
eas build -p android --profile preview
```

### iOS (requires Apple Developer account)

```bash
eas build -p ios --profile preview
```

## 📚 Documentation

- [Architecture Guide](./ARCHITECTURE.md)
- [Backend API Docs](../backend/README.md)
- [Expo Router Docs](https://expo.github.io/router/)

## 🤝 Contributing

1. Follow Feature-Sliced Design principles
2. Keep components pure (no business logic)
3. All state in Zustand stores
4. TypeScript strict mode enabled
5. Test on iOS, Android, and Web

## 📄 License

ISC
