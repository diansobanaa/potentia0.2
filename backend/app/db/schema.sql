-- Cara mengektrak schema dari database
-- Buka Schema Visualizer di Supabase
-- Copy as SQL di Pojok Kanan Atas

-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.AuditLog (
  log_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  action text NOT NULL,
  details jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT AuditLog_pkey PRIMARY KEY (log_id),
  CONSTRAINT AuditLog_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.Blocks (
  block_id uuid NOT NULL DEFAULT gen_random_uuid(),
  canvas_id uuid NOT NULL,
  parent_id uuid,
  y_order double precision NOT NULL,
  type USER-DEFINED NOT NULL DEFAULT 'text'::block_type,
  content text,
  properties jsonb,
  ai_metadata jsonb,
  CONSTRAINT Blocks_pkey PRIMARY KEY (block_id),
  CONSTRAINT Blocks_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.Canvas(canvas_id),
  CONSTRAINT Blocks_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.Blocks(block_id)
);
CREATE TABLE public.BlocksEmbeddings (
  embedding_id uuid NOT NULL DEFAULT gen_random_uuid(),
  block_id uuid NOT NULL UNIQUE,
  canvas_id uuid NOT NULL,
  content_checksum text,
  embedding USER-DEFINED,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT BlocksEmbeddings_pkey PRIMARY KEY (embedding_id),
  CONSTRAINT blockembeddings_block_id_fkey FOREIGN KEY (block_id) REFERENCES public.Blocks(block_id)
);
CREATE TABLE public.Canvas (
  canvas_id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid,
  user_id uuid,
  creator_user_id uuid NOT NULL,
  title text NOT NULL DEFAULT 'Untitled'::text,
  icon text,
  is_archived boolean DEFAULT false,
  canvas_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  summary_text text,
  CONSTRAINT Canvas_pkey PRIMARY KEY (canvas_id),
  CONSTRAINT Canvas_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.Workspaces(workspace_id),
  CONSTRAINT Canvas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id),
  CONSTRAINT Canvas_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.CanvasAccess (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  canvas_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'viewer'::canvas_role,
  granted_at timestamp with time zone DEFAULT now(),
  CONSTRAINT CanvasAccess_pkey PRIMARY KEY (id),
  CONSTRAINT CanvasAccess_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.Canvas(canvas_id),
  CONSTRAINT CanvasAccess_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.CanvasEmbeddings (
  embedding_id uuid NOT NULL DEFAULT gen_random_uuid(),
  canvas_id uuid NOT NULL,
  summary_checksum text,
  summary_embedding USER-DEFINED,
  model_version character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT CanvasEmbeddings_pkey PRIMARY KEY (embedding_id),
  CONSTRAINT canvasembeddings_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.Canvas(canvas_id)
);
CREATE TABLE public.ConversationSummaries (
  summary_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL UNIQUE,
  summary_content text NOT NULL,
  summary_vector USER-DEFINED,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT ConversationSummaries_pkey PRIMARY KEY (summary_id)
);
CREATE TABLE public.MessageEmbeddings (
  embedding_id uuid NOT NULL DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL UNIQUE,
  conversation_id uuid NOT NULL,
  embedding USER-DEFINED,
  model_version character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT MessageEmbeddings_pkey PRIMARY KEY (embedding_id)
);
CREATE TABLE public.SystemPrompts (
  system_prompt_id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  prompt_text text NOT NULL,
  version character varying,
  status character varying DEFAULT 'draft'::character varying CHECK (status::text = ANY (ARRAY['active'::character varying, 'draft'::character varying]::text[])),
  language_code character varying DEFAULT 'id'::character varying,
  CONSTRAINT SystemPrompts_pkey PRIMARY KEY (system_prompt_id)
);
CREATE TABLE public.Users (
  user_id uuid NOT NULL,
  name text,
  email text NOT NULL UNIQUE,
  role USER-DEFINED DEFAULT 'user'::user_role,
  status USER-DEFINED DEFAULT 'active'::user_status,
  subscription_tier text NOT NULL DEFAULT 'user'::text CHECK (subscription_tier = ANY (ARRAY['user'::text, 'pro'::text, 'admin'::text])),
  user_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT Users_pkey PRIMARY KEY (user_id),
  CONSTRAINT Users_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.WorkspaceInvitations (
  invitation_id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL,
  inviter_user_id uuid NOT NULL,
  invitee_user_id uuid,
  invitee_email text,
  role USER-DEFINED NOT NULL DEFAULT 'member'::member_role,
  type USER-DEFINED NOT NULL,
  status USER-DEFINED NOT NULL DEFAULT 'pending'::invitation_status,
  token text NOT NULL UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone,
  CONSTRAINT WorkspaceInvitations_pkey PRIMARY KEY (invitation_id),
  CONSTRAINT WorkspaceInvitations_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.Workspaces(workspace_id),
  CONSTRAINT WorkspaceInvitations_inviter_user_id_fkey FOREIGN KEY (inviter_user_id) REFERENCES public.Users(user_id),
  CONSTRAINT WorkspaceInvitations_invitee_user_id_fkey FOREIGN KEY (invitee_user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.WorkspaceMembers (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'member'::member_role,
  joined_at timestamp with time zone DEFAULT now(),
  CONSTRAINT WorkspaceMembers_pkey PRIMARY KEY (id),
  CONSTRAINT WorkspaceMembers_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.Workspaces(workspace_id),
  CONSTRAINT WorkspaceMembers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.Workspaces (
  workspace_id uuid NOT NULL DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL,
  name text NOT NULL,
  type USER-DEFINED NOT NULL DEFAULT 'personal'::workspace_type,
  workspace_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT Workspaces_pkey PRIMARY KEY (workspace_id),
  CONSTRAINT Workspaces_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.calendar_subscriptions (
  subscription_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  calendar_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'viewer'::calendar_subscription_role_enum,
  metadata jsonb,
  CONSTRAINT calendar_subscriptions_pkey PRIMARY KEY (subscription_id),
  CONSTRAINT calendar_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id),
  CONSTRAINT calendar_subscriptions_calendar_id_fkey FOREIGN KEY (calendar_id) REFERENCES public.calendars(calendar_id)
);
CREATE TABLE public.calendars (
  calendar_id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  owner_user_id uuid,
  workspace_id uuid,
  visibility USER-DEFINED NOT NULL DEFAULT 'private'::calendar_visibility_enum,
  metadata jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT calendars_pkey PRIMARY KEY (calendar_id),
  CONSTRAINT calendars_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.Users(user_id),
  CONSTRAINT calendars_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.Workspaces(workspace_id)
);
CREATE TABLE public.context (
  context_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  label USER-DEFINED,
  status text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT context_pkey PRIMARY KEY (context_id),
  CONSTRAINT context_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT context_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.conversations (
  conversation_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title text,
  status USER-DEFINED DEFAULT 'active'::conversation_status_enum,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  metadata jsonb,
  CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id)
);
CREATE TABLE public.decision_logs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid,
  message_id uuid,
  chosen_context_id uuid,
  score double precision,
  decision_reason text,
  details jsonb,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT decision_logs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.embedding_job_queue (
  queue_id uuid NOT NULL DEFAULT gen_random_uuid(),
  fk_id uuid NOT NULL,
  table_destination character varying NOT NULL,
  status USER-DEFINED DEFAULT 'pending'::queue_status_enum,
  priority integer DEFAULT 0,
  error_message text,
  retry_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT embedding_job_queue_pkey PRIMARY KEY (queue_id),
  CONSTRAINT embedding_job_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.instructions_memory (
  instruction_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  instruction_text text NOT NULL,
  priority integer DEFAULT 0,
  active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT instructions_memory_pkey PRIMARY KEY (instruction_id)
);
CREATE TABLE public.message_embedding_assistant (
  m_embedding_ai uuid NOT NULL DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL,
  embedding_vector USER-DEFINED NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  conversation_id uuid,
  user_id uuid,
  CONSTRAINT message_embedding_assistant_pkey PRIMARY KEY (m_embedding_ai),
  CONSTRAINT message_embedding_assistant_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id),
  CONSTRAINT message_embedding_assistant_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT message_embedding_assistant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.message_embedding_user (
  m_embedding_user uuid NOT NULL DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL,
  embedding_vector USER-DEFINED NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  conversation_id uuid,
  user_id uuid,
  CONSTRAINT message_embedding_user_pkey PRIMARY KEY (m_embedding_user),
  CONSTRAINT message_embedding_user_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id),
  CONSTRAINT message_embedding_user_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT message_embedding_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.messages (
  message_id uuid NOT NULL DEFAULT gen_random_uuid(),
  context_id uuid NOT NULL,
  role USER-DEFINED NOT NULL,
  content text,
  model_used character varying,
  token_count integer,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  conversation_id uuid,
  CONSTRAINT messages_pkey PRIMARY KEY (message_id),
  CONSTRAINT messages_context_id_fkey FOREIGN KEY (context_id) REFERENCES public.context(context_id),
  CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id),
  CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id)
);
CREATE TABLE public.prompt_snapshots (
  prompt_snapshot_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  message_id uuid,
  prompt_text text NOT NULL,
  ai_response_message_id uuid,
  token_total integer,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT prompt_snapshots_pkey PRIMARY KEY (prompt_snapshot_id),
  CONSTRAINT prompt_snapshots_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT prompt_snapshots_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id),
  CONSTRAINT prompt_snapshots_ai_response_message_id_fkey FOREIGN KEY (ai_response_message_id) REFERENCES public.messages(message_id),
  CONSTRAINT prompt_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.requeried_user_prompt (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL,
  prompt_text text,
  created_at timestamp with time zone DEFAULT now(),
  token_count integer,
  model_used character varying,
  CONSTRAINT requeried_user_prompt_pkey PRIMARY KEY (id),
  CONSTRAINT requeried_user_prompt_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id)
);
CREATE TABLE public.schedule_guests (
  guest_id uuid NOT NULL DEFAULT gen_random_uuid(),
  schedule_id uuid NOT NULL,
  user_id uuid,
  guest_email text,
  response_status USER-DEFINED NOT NULL DEFAULT 'pending'::rsvp_status_enum,
  role USER-DEFINED NOT NULL DEFAULT 'guest'::guest_role_enum,
  CONSTRAINT schedule_guests_pkey PRIMARY KEY (guest_id),
  CONSTRAINT schedule_guests_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.schedules(schedule_id),
  CONSTRAINT schedule_guests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.schedule_instances (
  instance_id uuid NOT NULL DEFAULT gen_random_uuid(),
  schedule_id uuid NOT NULL,
  calendar_id uuid NOT NULL,
  user_id uuid NOT NULL,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone NOT NULL,
  is_exception boolean NOT NULL DEFAULT false,
  is_deleted boolean NOT NULL DEFAULT false,
  CONSTRAINT schedule_instances_pkey PRIMARY KEY (instance_id),
  CONSTRAINT schedule_instances_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.schedules(schedule_id),
  CONSTRAINT schedule_instances_calendar_id_fkey FOREIGN KEY (calendar_id) REFERENCES public.calendars(calendar_id),
  CONSTRAINT schedule_instances_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.schedules (
  schedule_id uuid NOT NULL DEFAULT gen_random_uuid(),
  calendar_id uuid NOT NULL,
  title text NOT NULL,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone NOT NULL,
  schedule_metadata jsonb,
  rrule text,
  rdate ARRAY,
  exdate ARRAY,
  parent_schedule_id uuid,
  creator_user_id uuid NOT NULL,
  is_deleted boolean NOT NULL DEFAULT false,
  deleted_at timestamp with time zone,
  version integer NOT NULL DEFAULT 1,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT schedules_pkey PRIMARY KEY (schedule_id),
  CONSTRAINT schedules_calendar_id_fkey FOREIGN KEY (calendar_id) REFERENCES public.calendars(calendar_id),
  CONSTRAINT schedules_parent_schedule_id_fkey FOREIGN KEY (parent_schedule_id) REFERENCES public.schedules(schedule_id),
  CONSTRAINT schedules_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.summary_memory (
  summary_id uuid NOT NULL DEFAULT gen_random_uuid(),
  context_id uuid NOT NULL,
  summary_text text NOT NULL,
  token_count integer,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  CONSTRAINT summary_memory_pkey PRIMARY KEY (summary_id),
  CONSTRAINT summary_memory_context_id_fkey FOREIGN KEY (context_id) REFERENCES public.context(context_id),
  CONSTRAINT summary_memory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.summary_memory_embeddings (
  embedding_id uuid NOT NULL DEFAULT gen_random_uuid(),
  summary_id uuid NOT NULL,
  embedding_vector USER-DEFINED NOT NULL,
  model_name character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT summary_memory_embeddings_pkey PRIMARY KEY (embedding_id),
  CONSTRAINT summary_memory_embeddings_summary_id_fkey FOREIGN KEY (summary_id) REFERENCES public.summary_memory(summary_id)
);
CREATE TABLE public.tool_calls (
  toolcall_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  message_id uuid NOT NULL,
  tool_name character varying NOT NULL,
  input_data jsonb,
  output_data jsonb,
  created_at timestamp with time zone DEFAULT now(),
  executed_at timestamp with time zone,
  duration_ms integer,
  error_message text,
  user_id uuid,
  CONSTRAINT tool_calls_pkey PRIMARY KEY (toolcall_id),
  CONSTRAINT tool_calls_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT tool_calls_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id),
  CONSTRAINT tool_calls_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.Users(user_id)
);
CREATE TABLE public.user_preferences (
  preference_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  active boolean DEFAULT true,
  type text NOT NULL,
  description text NOT NULL,
  trigger_text text,
  confidence_score double precision NOT NULL DEFAULT 0.0,
  priority integer DEFAULT 0,
  last_accessed_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_preferences_pkey PRIMARY KEY (preference_id),
  CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.user_semantic_memories (
  memory_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  content text NOT NULL,
  type text DEFAULT 'MEMORI'::text,
  trigger_text text,
  confidence_score double precision,
  embedding USER-DEFINED NOT NULL,
  CONSTRAINT user_semantic_memories_pkey PRIMARY KEY (memory_id),
  CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id)
);