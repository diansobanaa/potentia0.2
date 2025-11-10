# Rencana Refactoring workspace_queries.py

## Analisis File Saat Ini

**File:** `backend/app/db/queries/workspace/workspace_queries.py`
**Total Baris:** 460 baris
**Total Fungsi:** 14 fungsi

## Pengelompokan Fungsi

### 1. CRUD Workspace (Induk) - 4 fungsi
- `create_workspace` - Membuat workspace baru
- `get_workspace_by_id` - Mengambil detail workspace
- `update_workspace` - Memperbarui workspace
- `delete_workspace` - Menghapus workspace

**File Baru:** `workspace_crud.py` (~100 baris)

### 2. Paginasi Workspace - 1 fungsi
- `get_user_workspaces_paginated` - Mengambil daftar workspace dengan paginasi

**File Baru:** `workspace_list.py` (~50 baris)

### 3. CRUD Anggota Workspace - 5 fungsi
- `check_user_membership` - Memeriksa keanggotaan user
- `add_member_to_workspace` - Menambahkan anggota
- `list_workspace_members` - Mengambil daftar anggota
- `update_workspace_member_role` - Memperbarui role anggota
- `remove_workspace_member` - Menghapus anggota

**File Baru:** `workspace_members.py` (~150 baris)

### 4. Logika Undangan (Invitations) - 4 fungsi
- `create_workspace_invitation` - Membuat undangan baru
- `_find_invitation_by_token` - Helper: Mencari undangan by token
- `_delete_invitation_by_token` - Helper: Menghapus undangan by token
- `respond_to_workspace_invitation` - Orkestrator: Accept/reject undangan

**File Baru:** `workspace_invitations.py` (~150 baris)

## Struktur File Baru

```
backend/app/db/queries/workspace/
├── __init__.py                    # Export semua fungsi (backward compatibility)
├── workspace_crud.py              # CRUD workspace (4 fungsi)
├── workspace_list.py              # List/paginasi workspace (1 fungsi)
├── workspace_members.py           # CRUD anggota workspace (5 fungsi)
└── workspace_invitations.py      # Logika undangan (4 fungsi)
```

## Dependencies yang Perlu Diperhatikan

### Import dari workspace_queries:
1. `backend/app/api/v1/endpoints/workspace_members.py`:
   - `list_workspace_members`
   - `create_workspace_invitation`
   - `update_workspace_member_role`
   - `remove_workspace_member`

2. `backend/app/api/v1/endpoints/invitations.py`:
   - `respond_to_workspace_invitation`

3. `backend/app/core/dependencies.py`:
   - `check_user_membership`

4. `backend/app/services/workspace/workspace_service.py`:
   - `create_workspace`
   - `add_member_to_workspace`
   - `get_user_workspaces_paginated`
   - `get_workspace_by_id`
   - `update_workspace`
   - `delete_workspace`

## Strategi Backward Compatibility

Menggunakan `__init__.py` untuk export semua fungsi agar import yang sudah ada tetap berfungsi:

```python
# __init__.py
from .workspace_crud import (
    create_workspace,
    get_workspace_by_id,
    update_workspace,
    delete_workspace
)
from .workspace_list import get_user_workspaces_paginated
from .workspace_members import (
    check_user_membership,
    add_member_to_workspace,
    list_workspace_members,
    update_workspace_member_role,
    remove_workspace_member
)
from .workspace_invitations import (
    create_workspace_invitation,
    respond_to_workspace_invitation
)
```

## Keuntungan Refactoring

1. **Modularitas**: Setiap file fokus pada domain tertentu
2. **Maintainability**: Lebih mudah mencari dan memperbaiki bug
3. **Readability**: File lebih pendek dan mudah dibaca
4. **Testability**: Lebih mudah menulis unit test per domain
5. **Scalability**: Lebih mudah menambah fitur baru tanpa membuat file terlalu panjang

## Estimasi Ukuran File

- `workspace_crud.py`: ~100 baris (4 fungsi)
- `workspace_list.py`: ~50 baris (1 fungsi)
- `workspace_members.py`: ~150 baris (5 fungsi)
- `workspace_invitations.py`: ~150 baris (4 fungsi)
- `__init__.py`: ~20 baris (export)

**Total:** ~470 baris (sama dengan file asli, tapi lebih terorganisir)

