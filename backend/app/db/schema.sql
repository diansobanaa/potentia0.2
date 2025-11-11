-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.block_operations (
  op_id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_op_id text NOT NULL,
  block_id uuid NOT NULL,
  user_id uuid NOT NULL,
  canvas_id uuid NOT NULL,
  server_seq bigint NOT NULL,
  action USER-DEFINED NOT NULL,
  status USER-DEFINED NOT NULL DEFAULT 'pending'::operation_status,
  payload jsonb,
  created_at timestamp with time zone DEFAULT now(),
  processed_at timestamp with time zone,
  error_message text,
  CONSTRAINT block_operations_pkey PRIMARY KEY (op_id),
  CONSTRAINT block_operations_block_id_fkey FOREIGN KEY (block_id) REFERENCES public.blocks(block_id),
  CONSTRAINT block_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id),
  CONSTRAINT block_operations_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.canvas(canvas_id)
);
CREATE TABLE public.blocks (
  block_id uuid NOT NULL DEFAULT gen_random_uuid(),
  canvas_id uuid NOT NULL,
  parent_id uuid,
  y_order text NOT NULL,
  type text NOT NULL DEFAULT 'text'::text,
  content text,
  properties jsonb,
  ai_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  created_by uuid,
  version integer NOT NULL DEFAULT 1,
  updated_at timestamp with time zone DEFAULT now(),
  updated_by uuid,
  vector USER-DEFINED,
  generation_session_id uuid,
  CONSTRAINT blocks_pkey PRIMARY KEY (block_id),
  CONSTRAINT blocks_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.canvas(canvas_id),
  CONSTRAINT blocks_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.blocks(block_id),
  CONSTRAINT blocks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id),
  CONSTRAINT blocks_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(user_id)
);
CREATE TABLE public.calendar_subscriptions (
  subscription_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  calendar_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'viewer'::calendar_subscription_role_enum,
  metadata jsonb,
  CONSTRAINT calendar_subscriptions_pkey PRIMARY KEY (subscription_id),
  CONSTRAINT calendar_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id),
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
  CONSTRAINT calendars_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(user_id),
  CONSTRAINT calendars_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(workspace_id)
);
CREATE TABLE public.canvas (
  canvas_id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid,
  owner_user_id uuid,
  creator_user_id uuid NOT NULL,
  title text NOT NULL DEFAULT 'Untitled'::text,
  icon text,
  is_archived boolean NOT NULL DEFAULT false,
  canvas_metadata jsonb,
  summary_text text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT canvas_pkey PRIMARY KEY (canvas_id),
  CONSTRAINT canvas_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.users(user_id),
  CONSTRAINT canvas_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(user_id),
  CONSTRAINT canvas_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(workspace_id)
);
CREATE TABLE public.canvas_access (
  access_id uuid NOT NULL DEFAULT gen_random_uuid(),
  canvas_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'viewer'::canvas_role,
  granted_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT canvas_access_pkey PRIMARY KEY (access_id),
  CONSTRAINT canvas_access_canvas_id_fkey FOREIGN KEY (canvas_id) REFERENCES public.canvas(canvas_id),
  CONSTRAINT canvas_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.context (
  context_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  user_id uuid NOT NULL,
  label text,
  status text DEFAULT 'active'::text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT context_pkey PRIMARY KEY (context_id),
  CONSTRAINT context_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT context_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.conversations (
  conversation_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title text,
  status USER-DEFINED DEFAULT 'active'::conversation_status_enum,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  metadata jsonb,
  CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id),
  CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.decision_logs (
  log_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid,
  message_id uuid,
  user_id uuid,
  chosen_context_id uuid,
  score double precision,
  decision_reason text,
  details jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT decision_logs_pkey PRIMARY KEY (log_id),
  CONSTRAINT decision_logs_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT decision_logs_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(message_id),
  CONSTRAINT decision_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.embedding_job_queue (
  queue_id uuid NOT NULL DEFAULT gen_random_uuid(),
  fk_id uuid NOT NULL,
  table_destination character varying NOT NULL,
  user_id uuid,
  status USER-DEFINED DEFAULT 'pending'::queue_status_enum,
  priority integer DEFAULT 0,
  error_message text,
  retry_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT embedding_job_queue_pkey PRIMARY KEY (queue_id),
  CONSTRAINT embedding_job_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.messages (
  message_id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  context_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL,
  content text,
  model_used character varying,
  token_count integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT messages_pkey PRIMARY KEY (message_id),
  CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  CONSTRAINT messages_context_id_fkey FOREIGN KEY (context_id) REFERENCES public.context(context_id),
  CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
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
  CONSTRAINT schedule_guests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
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
  CONSTRAINT schedule_instances_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
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
  CONSTRAINT schedules_creator_user_id_fkey FOREIGN KEY (creator_user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.summary_memory (
  summary_id uuid NOT NULL DEFAULT gen_random_uuid(),
  context_id uuid NOT NULL,
  user_id uuid NOT NULL,
  summary_text text NOT NULL,
  token_count integer,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT summary_memory_pkey PRIMARY KEY (summary_id),
  CONSTRAINT summary_memory_context_id_fkey FOREIGN KEY (context_id) REFERENCES public.context(context_id),
  CONSTRAINT summary_memory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
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
CREATE TABLE public.system_audit (
  audit_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  action text NOT NULL,
  entity text NOT NULL,
  entity_id uuid,
  details jsonb,
  client_op_id text,
  server_seq bigint,
  status USER-DEFINED NOT NULL,
  ip_address inet,
  user_agent text,
  session_id uuid,
  response_time_ms integer,
  affected_rows integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT system_audit_pkey PRIMARY KEY (audit_id),
  CONSTRAINT system_audit_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.system_prompts (
  system_prompt_id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  prompt_text text NOT NULL,
  version character varying,
  status character varying DEFAULT 'draft'::character varying,
  language_code character varying DEFAULT 'id'::character varying,
  CONSTRAINT system_prompts_pkey PRIMARY KEY (system_prompt_id)
);
CREATE TABLE public.user_preferences (
  preference_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  type USER-DEFINED NOT NULL,
  description text NOT NULL,
  trigger_text text,
  confidence_score double precision NOT NULL DEFAULT 0.0,
  priority integer DEFAULT 0,
  active boolean DEFAULT true,
  last_accessed_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_preferences_pkey PRIMARY KEY (preference_id),
  CONSTRAINT user_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.user_semantic_memories (
  memory_id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  content text NOT NULL,
  type text DEFAULT 'MEMORI'::text,
  trigger_text text,
  confidence_score double precision,
  embedding USER-DEFINED NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_semantic_memories_pkey PRIMARY KEY (memory_id),
  CONSTRAINT user_semantic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.users (
  user_id uuid NOT NULL,
  name text,
  email text NOT NULL UNIQUE,
  role USER-DEFINED DEFAULT 'user'::user_role,
  status USER-DEFINED DEFAULT 'active'::user_status,
  subscription_tier text NOT NULL DEFAULT 'user'::text CHECK (subscription_tier = ANY (ARRAY['user'::text, 'pro'::text, 'admin'::text])),
  user_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (user_id),
  CONSTRAINT Users_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.workspace_invitations (
  invitation_id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL,
  inviter_user_id uuid NOT NULL,
  invitee_user_id uuid,
  invitee_email text,
  role USER-DEFINED NOT NULL DEFAULT 'member'::member_role,
  type USER-DEFINED NOT NULL,
  status USER-DEFINED NOT NULL DEFAULT 'pending'::invitation_status,
  token text NOT NULL DEFAULT (uuid_generate_v4())::text UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone,
  CONSTRAINT workspace_invitations_pkey PRIMARY KEY (invitation_id),
  CONSTRAINT workspace_invitations_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(workspace_id),
  CONSTRAINT workspace_invitations_inviter_user_id_fkey FOREIGN KEY (inviter_user_id) REFERENCES public.users(user_id),
  CONSTRAINT workspace_invitations_invitee_user_id_fkey FOREIGN KEY (invitee_user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.workspace_members (
  member_id uuid NOT NULL DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'member'::member_role,
  joined_at timestamp with time zone DEFAULT now(),
  CONSTRAINT workspace_members_pkey PRIMARY KEY (member_id),
  CONSTRAINT workspace_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(workspace_id),
  CONSTRAINT workspace_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.workspaces (
  workspace_id uuid NOT NULL DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL,
  name text NOT NULL,
  type USER-DEFINED NOT NULL DEFAULT 'personal'::workspace_type,
  workspace_metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT workspaces_pkey PRIMARY KEY (workspace_id),
  CONSTRAINT workspaces_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(user_id)
);