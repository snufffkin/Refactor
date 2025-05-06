--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Homebrew)
-- Dumped by pg_dump version 14.17 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: assignment_history; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.assignment_history (
    history_id integer NOT NULL,
    assignment_id integer NOT NULL,
    old_status character varying(20),
    new_status character varying(20) NOT NULL,
    changed_by integer NOT NULL,
    change_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    comment text
);


ALTER TABLE public.assignment_history OWNER TO romannikitin;

--
-- Name: assignment_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: romannikitin
--

CREATE SEQUENCE public.assignment_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.assignment_history_history_id_seq OWNER TO romannikitin;

--
-- Name: assignment_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romannikitin
--

ALTER SEQUENCE public.assignment_history_history_id_seq OWNED BY public.assignment_history.history_id;


--
-- Name: card_assignments; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.card_assignments (
    assignment_id integer NOT NULL,
    card_id integer NOT NULL,
    user_id integer NOT NULL,
    status character varying(20) DEFAULT 'in_progress'::character varying NOT NULL,
    assigned_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.card_assignments OWNER TO romannikitin;

--
-- Name: card_assignments_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: romannikitin
--

CREATE SEQUENCE public.card_assignments_assignment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.card_assignments_assignment_id_seq OWNER TO romannikitin;

--
-- Name: card_assignments_assignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romannikitin
--

ALTER SEQUENCE public.card_assignments_assignment_id_seq OWNED BY public.card_assignments.assignment_id;


--
-- Name: card_risk_cache; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.card_risk_cache (
    card_id bigint,
    risk double precision,
    updated_at timestamp with time zone
);


ALTER TABLE public.card_risk_cache OWNER TO romannikitin;

--
-- Name: card_status; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.card_status (
    card_id bigint NOT NULL,
    status text DEFAULT 'new'::text,
    updated_by text,
    updated_at text
);


ALTER TABLE public.card_status OWNER TO romannikitin;

--
-- Name: cards_flat; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.cards_flat (
    program text,
    module text,
    module_order bigint,
    lesson text,
    lesson_order bigint,
    gz text,
    gz_id bigint,
    card_id bigint,
    card_type text,
    card_url text,
    total_attempts bigint,
    attempted_share double precision,
    success_rate double precision,
    first_try_success_rate double precision,
    complaint_rate double precision,
    complaints_total bigint,
    discrimination_avg double precision,
    success_attempts_rate double precision,
    status text,
    updated_at text
);


ALTER TABLE public.cards_flat OWNER TO romannikitin;

--
-- Name: cards_metrics; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.cards_metrics (
    card_id bigint,
    total_attempts bigint,
    attempted_share double precision,
    success_rate double precision,
    first_try_success_rate double precision,
    complaint_rate double precision,
    complaints_total bigint,
    discrimination_avg double precision,
    success_attempts_rate double precision
);


ALTER TABLE public.cards_metrics OWNER TO romannikitin;

--
-- Name: cards_structure; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.cards_structure (
    program text,
    module text,
    module_order bigint,
    lesson text,
    lesson_order bigint,
    gz text,
    gz_id bigint,
    card_id bigint,
    card_type text,
    card_url text
);


ALTER TABLE public.cards_structure OWNER TO romannikitin;

--
-- Name: cards_mv; Type: VIEW; Schema: public; Owner: romannikitin
--

CREATE VIEW public.cards_mv AS
 SELECT s.program,
    s.module,
    s.module_order,
    s.lesson,
    s.lesson_order,
    s.gz,
    s.gz_id,
    s.card_id,
    s.card_type,
    s.card_url,
    m.total_attempts,
    m.attempted_share,
    m.success_rate,
    m.first_try_success_rate,
    m.complaint_rate,
    m.complaints_total,
    m.discrimination_avg,
    m.success_attempts_rate,
    COALESCE(st.status, 'new'::text) AS status,
    st.updated_at
   FROM ((public.cards_structure s
     LEFT JOIN public.cards_metrics m USING (card_id))
     LEFT JOIN public.card_status st USING (card_id));


ALTER TABLE public.cards_mv OWNER TO romannikitin;

--
-- Name: mv_cards_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_cards_mv AS
 SELECT s.program,
    s.module,
    s.module_order,
    s.lesson,
    s.lesson_order,
    s.gz,
    s.gz_id,
    s.card_id,
    s.card_type,
    s.card_url,
    m.total_attempts,
    m.attempted_share,
    m.success_rate,
    m.first_try_success_rate,
    m.complaint_rate,
    m.complaints_total,
    m.discrimination_avg,
    m.success_attempts_rate,
    COALESCE(st.status, 'new'::text) AS status,
    st.updated_at
   FROM ((public.cards_structure s
     JOIN public.cards_metrics m USING (card_id))
     LEFT JOIN public.card_status st USING (card_id))
  WITH NO DATA;


ALTER TABLE public.mv_cards_mv OWNER TO romannikitin;

--
-- Name: mv_gz_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_gz_stats AS
 SELECT mv_cards_mv.program,
    mv_cards_mv.module,
    mv_cards_mv.module_order,
    mv_cards_mv.lesson,
    mv_cards_mv.lesson_order,
    mv_cards_mv.gz,
    mv_cards_mv.gz_id,
    count(DISTINCT mv_cards_mv.card_id) AS card_count,
    avg(mv_cards_mv.success_rate) AS avg_success_rate,
    avg(mv_cards_mv.complaint_rate) AS avg_complaint_rate,
    avg(mv_cards_mv.attempted_share) AS avg_attempted_share,
    avg(mv_cards_mv.discrimination_avg) AS avg_discrimination,
    sum(mv_cards_mv.total_attempts) AS total_attempts_sum,
    count(DISTINCT mv_cards_mv.card_type) AS card_type_count,
    max(mv_cards_mv.updated_at) AS last_updated
   FROM public.mv_cards_mv
  GROUP BY mv_cards_mv.program, mv_cards_mv.module, mv_cards_mv.module_order, mv_cards_mv.lesson, mv_cards_mv.lesson_order, mv_cards_mv.gz, mv_cards_mv.gz_id
  ORDER BY mv_cards_mv.program, mv_cards_mv.module_order, mv_cards_mv.lesson_order, mv_cards_mv.gz
  WITH NO DATA;


ALTER TABLE public.mv_gz_stats OWNER TO romannikitin;

--
-- Name: mv_gz_risk; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_gz_risk AS
 SELECT g.program,
    g.module,
    g.module_order,
    g.lesson,
    g.lesson_order,
    g.gz,
    g.gz_id,
    g.card_count,
    g.avg_success_rate,
    g.avg_complaint_rate,
    avg(r.risk) AS avg_risk,
    g.last_updated
   FROM ((public.mv_gz_stats g
     JOIN public.mv_cards_mv c ON (((g.program = c.program) AND (g.module = c.module) AND (g.lesson = c.lesson) AND (g.gz = c.gz))))
     JOIN public.card_risk_cache r ON ((c.card_id = r.card_id)))
  GROUP BY g.program, g.module, g.module_order, g.lesson, g.lesson_order, g.gz, g.gz_id, g.card_count, g.avg_success_rate, g.avg_complaint_rate, g.last_updated
  ORDER BY g.program, g.module_order, g.lesson_order
  WITH NO DATA;


ALTER TABLE public.mv_gz_risk OWNER TO romannikitin;

--
-- Name: mv_lesson_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_lesson_stats AS
 SELECT mv_cards_mv.program,
    mv_cards_mv.module,
    mv_cards_mv.module_order,
    mv_cards_mv.lesson,
    mv_cards_mv.lesson_order,
    count(DISTINCT mv_cards_mv.card_id) AS card_count,
    avg(mv_cards_mv.success_rate) AS avg_success_rate,
    avg(mv_cards_mv.complaint_rate) AS avg_complaint_rate,
    avg(mv_cards_mv.attempted_share) AS avg_attempted_share,
    avg(mv_cards_mv.discrimination_avg) AS avg_discrimination,
    sum(mv_cards_mv.total_attempts) AS total_attempts_sum,
    count(DISTINCT mv_cards_mv.gz) AS gz_count,
    max(mv_cards_mv.updated_at) AS last_updated
   FROM public.mv_cards_mv
  GROUP BY mv_cards_mv.program, mv_cards_mv.module, mv_cards_mv.module_order, mv_cards_mv.lesson, mv_cards_mv.lesson_order
  ORDER BY mv_cards_mv.program, mv_cards_mv.module_order, mv_cards_mv.lesson_order
  WITH NO DATA;


ALTER TABLE public.mv_lesson_stats OWNER TO romannikitin;

--
-- Name: mv_lesson_risk; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_lesson_risk AS
 SELECT l.program,
    l.module,
    l.module_order,
    l.lesson,
    l.lesson_order,
    l.card_count,
    l.avg_success_rate,
    l.avg_complaint_rate,
    avg(r.risk) AS avg_risk,
    l.last_updated
   FROM ((public.mv_lesson_stats l
     JOIN public.mv_cards_mv c ON (((l.program = c.program) AND (l.module = c.module) AND (l.lesson = c.lesson))))
     JOIN public.card_risk_cache r ON ((c.card_id = r.card_id)))
  GROUP BY l.program, l.module, l.module_order, l.lesson, l.lesson_order, l.card_count, l.avg_success_rate, l.avg_complaint_rate, l.last_updated
  ORDER BY l.program, l.module_order, l.lesson_order
  WITH NO DATA;


ALTER TABLE public.mv_lesson_risk OWNER TO romannikitin;

--
-- Name: mv_module_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_module_stats AS
 SELECT mv_cards_mv.program,
    mv_cards_mv.module,
    mv_cards_mv.module_order,
    count(DISTINCT mv_cards_mv.card_id) AS card_count,
    avg(mv_cards_mv.success_rate) AS avg_success_rate,
    avg(mv_cards_mv.complaint_rate) AS avg_complaint_rate,
    avg(mv_cards_mv.attempted_share) AS avg_attempted_share,
    avg(mv_cards_mv.discrimination_avg) AS avg_discrimination,
    sum(mv_cards_mv.total_attempts) AS total_attempts_sum,
    count(DISTINCT mv_cards_mv.lesson) AS lesson_count,
    count(DISTINCT mv_cards_mv.gz) AS gz_count,
    max(mv_cards_mv.updated_at) AS last_updated
   FROM public.mv_cards_mv
  GROUP BY mv_cards_mv.program, mv_cards_mv.module, mv_cards_mv.module_order
  ORDER BY mv_cards_mv.program, mv_cards_mv.module_order
  WITH NO DATA;


ALTER TABLE public.mv_module_stats OWNER TO romannikitin;

--
-- Name: mv_module_risk; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_module_risk AS
 SELECT m.program,
    m.module,
    m.module_order,
    m.card_count,
    m.avg_success_rate,
    m.avg_complaint_rate,
    avg(r.risk) AS avg_risk,
    m.last_updated
   FROM ((public.mv_module_stats m
     JOIN public.mv_cards_mv c ON (((m.program = c.program) AND (m.module = c.module))))
     JOIN public.card_risk_cache r ON ((c.card_id = r.card_id)))
  GROUP BY m.program, m.module, m.module_order, m.card_count, m.avg_success_rate, m.avg_complaint_rate, m.last_updated
  ORDER BY m.program, m.module_order
  WITH NO DATA;


ALTER TABLE public.mv_module_risk OWNER TO romannikitin;

--
-- Name: mv_program_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_program_stats AS
 SELECT mv_cards_mv.program,
    count(DISTINCT mv_cards_mv.card_id) AS card_count,
    avg(mv_cards_mv.success_rate) AS avg_success_rate,
    avg(mv_cards_mv.complaint_rate) AS avg_complaint_rate,
    avg(mv_cards_mv.attempted_share) AS avg_attempted_share,
    avg(mv_cards_mv.discrimination_avg) AS avg_discrimination,
    sum(mv_cards_mv.total_attempts) AS total_attempts_sum,
    count(DISTINCT mv_cards_mv.module) AS module_count,
    count(DISTINCT mv_cards_mv.lesson) AS lesson_count,
    count(DISTINCT mv_cards_mv.gz) AS gz_count,
    max(mv_cards_mv.updated_at) AS last_updated
   FROM public.mv_cards_mv
  GROUP BY mv_cards_mv.program
  WITH NO DATA;


ALTER TABLE public.mv_program_stats OWNER TO romannikitin;

--
-- Name: mv_program_risk; Type: MATERIALIZED VIEW; Schema: public; Owner: romannikitin
--

CREATE MATERIALIZED VIEW public.mv_program_risk AS
 SELECT p.program,
    p.card_count,
    p.avg_success_rate,
    p.avg_complaint_rate,
    avg(r.risk) AS avg_risk,
    p.last_updated
   FROM ((public.mv_program_stats p
     JOIN public.mv_cards_mv c ON ((p.program = c.program)))
     JOIN public.card_risk_cache r ON ((c.card_id = r.card_id)))
  GROUP BY p.program, p.card_count, p.avg_success_rate, p.avg_complaint_rate, p.last_updated
  WITH NO DATA;


ALTER TABLE public.mv_program_risk OWNER TO romannikitin;

--
-- Name: teacher_reviews; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.teacher_reviews (
    program text,
    module text,
    lesson text,
    presentation_rate double precision,
    presentation_like text,
    presentation_dislike text,
    workbook_rate double precision,
    workbook_like text,
    workbook_dislike text,
    addmaterial_stat double precision,
    addmaterial_rate double precision,
    addmaterial_like text,
    addmaterial_dislike text,
    overall_stat double precision,
    interest_stat double precision,
    interest_dislike text,
    interest_like text,
    complexity_stat double precision,
    complexity_to_simplify text,
    complexity_to_complicate text
);


ALTER TABLE public.teacher_reviews OWNER TO romannikitin;

--
-- Name: top10_by_group; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.top10_by_group (
    gz text,
    card_id bigint,
    risk double precision,
    rn bigint
);


ALTER TABLE public.top10_by_group OWNER TO romannikitin;

--
-- Name: users; Type: TABLE; Schema: public; Owner: romannikitin
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(128) NOT NULL,
    email character varying(100),
    full_name character varying(100),
    role character varying(20) DEFAULT 'methodist'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO romannikitin;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: romannikitin
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_user_id_seq OWNER TO romannikitin;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romannikitin
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: assignment_history history_id; Type: DEFAULT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.assignment_history ALTER COLUMN history_id SET DEFAULT nextval('public.assignment_history_history_id_seq'::regclass);


--
-- Name: card_assignments assignment_id; Type: DEFAULT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.card_assignments ALTER COLUMN assignment_id SET DEFAULT nextval('public.card_assignments_assignment_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: assignment_history assignment_history_pkey; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.assignment_history
    ADD CONSTRAINT assignment_history_pkey PRIMARY KEY (history_id);


--
-- Name: card_assignments card_assignments_card_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.card_assignments
    ADD CONSTRAINT card_assignments_card_id_user_id_key UNIQUE (card_id, user_id);


--
-- Name: card_assignments card_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.card_assignments
    ADD CONSTRAINT card_assignments_pkey PRIMARY KEY (assignment_id);


--
-- Name: card_status idx_16393_card_status_pkey; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.card_status
    ADD CONSTRAINT idx_16393_card_status_pkey PRIMARY KEY (card_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_flat_card_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_card_id ON public.cards_flat USING btree (card_id);


--
-- Name: idx_flat_filters; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_filters ON public.cards_flat USING btree (program, module, lesson, gz);


--
-- Name: idx_flat_gz; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_gz ON public.cards_flat USING btree (gz);


--
-- Name: idx_flat_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_lesson ON public.cards_flat USING btree (lesson);


--
-- Name: idx_flat_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_module ON public.cards_flat USING btree (module);


--
-- Name: idx_flat_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_orders ON public.cards_flat USING btree (module_order, lesson_order);


--
-- Name: idx_flat_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_program ON public.cards_flat USING btree (program);


--
-- Name: idx_flat_status; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_flat_status ON public.cards_flat USING btree (status);


--
-- Name: idx_gz_risk_all_filter; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_all_filter ON public.mv_gz_risk USING btree (program, module, lesson, gz);


--
-- Name: idx_gz_risk_avg_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_avg_risk ON public.mv_gz_risk USING btree (avg_risk);


--
-- Name: idx_gz_risk_gz; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_gz ON public.mv_gz_risk USING btree (gz);


--
-- Name: idx_gz_risk_gz_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_gz_id ON public.mv_gz_risk USING btree (gz_id);


--
-- Name: idx_gz_risk_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_lesson ON public.mv_gz_risk USING btree (lesson);


--
-- Name: idx_gz_risk_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_module ON public.mv_gz_risk USING btree (module);


--
-- Name: idx_gz_risk_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_program ON public.mv_gz_risk USING btree (program);


--
-- Name: idx_gz_risk_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_program_module ON public.mv_gz_risk USING btree (program, module);


--
-- Name: idx_gz_risk_program_module_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_risk_program_module_lesson ON public.mv_gz_risk USING btree (program, module, lesson);


--
-- Name: idx_gz_stats_all_filter; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_all_filter ON public.mv_gz_stats USING btree (program, module, lesson, gz);


--
-- Name: idx_gz_stats_complaint; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_complaint ON public.mv_gz_stats USING btree (avg_complaint_rate);


--
-- Name: idx_gz_stats_gz; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_gz ON public.mv_gz_stats USING btree (gz);


--
-- Name: idx_gz_stats_gz_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_gz_id ON public.mv_gz_stats USING btree (gz_id);


--
-- Name: idx_gz_stats_lesson_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_lesson_order ON public.mv_gz_stats USING btree (lesson_order);


--
-- Name: idx_gz_stats_module_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_module_order ON public.mv_gz_stats USING btree (module_order);


--
-- Name: idx_gz_stats_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_orders ON public.mv_gz_stats USING btree (module_order, lesson_order);


--
-- Name: idx_gz_stats_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_program_module ON public.mv_gz_stats USING btree (program, module);


--
-- Name: idx_gz_stats_program_module_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_program_module_lesson ON public.mv_gz_stats USING btree (program, module, lesson);


--
-- Name: idx_gz_stats_program_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_program_orders ON public.mv_gz_stats USING btree (program, module_order, lesson_order);


--
-- Name: idx_gz_stats_success; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_gz_stats_success ON public.mv_gz_stats USING btree (avg_success_rate);


--
-- Name: idx_lesson_risk_avg_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_avg_risk ON public.mv_lesson_risk USING btree (avg_risk);


--
-- Name: idx_lesson_risk_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_lesson ON public.mv_lesson_risk USING btree (lesson);


--
-- Name: idx_lesson_risk_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_module ON public.mv_lesson_risk USING btree (module);


--
-- Name: idx_lesson_risk_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_orders ON public.mv_lesson_risk USING btree (module_order, lesson_order);


--
-- Name: idx_lesson_risk_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_program ON public.mv_lesson_risk USING btree (program);


--
-- Name: idx_lesson_risk_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_program_module ON public.mv_lesson_risk USING btree (program, module);


--
-- Name: idx_lesson_risk_program_module_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_risk_program_module_lesson ON public.mv_lesson_risk USING btree (program, module, lesson);


--
-- Name: idx_lesson_stats_complaint; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_complaint ON public.mv_lesson_stats USING btree (avg_complaint_rate);


--
-- Name: idx_lesson_stats_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_lesson ON public.mv_lesson_stats USING btree (lesson);


--
-- Name: idx_lesson_stats_lesson_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_lesson_order ON public.mv_lesson_stats USING btree (lesson_order);


--
-- Name: idx_lesson_stats_module_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_module_order ON public.mv_lesson_stats USING btree (module_order);


--
-- Name: idx_lesson_stats_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_orders ON public.mv_lesson_stats USING btree (module_order, lesson_order);


--
-- Name: idx_lesson_stats_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_program_module ON public.mv_lesson_stats USING btree (program, module);


--
-- Name: idx_lesson_stats_program_module_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_program_module_lesson ON public.mv_lesson_stats USING btree (program, module, lesson);


--
-- Name: idx_lesson_stats_program_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_program_orders ON public.mv_lesson_stats USING btree (program, module_order, lesson_order);


--
-- Name: idx_lesson_stats_success; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_lesson_stats_success ON public.mv_lesson_stats USING btree (avg_success_rate);


--
-- Name: idx_module_risk_avg_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_risk_avg_risk ON public.mv_module_risk USING btree (avg_risk);


--
-- Name: idx_module_risk_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_risk_module ON public.mv_module_risk USING btree (module);


--
-- Name: idx_module_risk_module_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_risk_module_order ON public.mv_module_risk USING btree (module_order);


--
-- Name: idx_module_risk_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_risk_program ON public.mv_module_risk USING btree (program);


--
-- Name: idx_module_risk_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_risk_program_module ON public.mv_module_risk USING btree (program, module);


--
-- Name: idx_module_stats_complaint; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_complaint ON public.mv_module_stats USING btree (avg_complaint_rate);


--
-- Name: idx_module_stats_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_module ON public.mv_module_stats USING btree (module);


--
-- Name: idx_module_stats_module_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_module_order ON public.mv_module_stats USING btree (module_order);


--
-- Name: idx_module_stats_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_program ON public.mv_module_stats USING btree (program);


--
-- Name: idx_module_stats_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_program_module ON public.mv_module_stats USING btree (program, module);


--
-- Name: idx_module_stats_program_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_program_order ON public.mv_module_stats USING btree (program, module_order);


--
-- Name: idx_module_stats_success; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_module_stats_success ON public.mv_module_stats USING btree (avg_success_rate);


--
-- Name: idx_mv_card_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_card_id ON public.mv_cards_mv USING btree (card_id);


--
-- Name: idx_mv_filters; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_filters ON public.mv_cards_mv USING btree (program, module, lesson, gz);


--
-- Name: idx_mv_gz; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_gz ON public.mv_cards_mv USING btree (gz);


--
-- Name: idx_mv_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_lesson ON public.mv_cards_mv USING btree (lesson);


--
-- Name: idx_mv_lesson_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_lesson_order ON public.mv_cards_mv USING btree (lesson_order);


--
-- Name: idx_mv_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_module ON public.mv_cards_mv USING btree (module);


--
-- Name: idx_mv_module_order; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_module_order ON public.mv_cards_mv USING btree (module_order);


--
-- Name: idx_mv_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_program ON public.mv_cards_mv USING btree (program);


--
-- Name: idx_mv_program_module; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_program_module ON public.mv_cards_mv USING btree (program, module);


--
-- Name: idx_mv_program_module_lesson; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_program_module_lesson ON public.mv_cards_mv USING btree (program, module, lesson);


--
-- Name: idx_mv_program_module_orders; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_program_module_orders ON public.mv_cards_mv USING btree (program, module_order, lesson_order);


--
-- Name: idx_mv_status; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_mv_status ON public.mv_cards_mv USING btree (status);


--
-- Name: idx_program_risk_avg_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_program_risk_avg_risk ON public.mv_program_risk USING btree (avg_risk);


--
-- Name: idx_program_risk_program; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_program_risk_program ON public.mv_program_risk USING btree (program);


--
-- Name: idx_program_stats; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_program_stats ON public.mv_program_stats USING btree (program);


--
-- Name: idx_program_stats_complaint; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_program_stats_complaint ON public.mv_program_stats USING btree (avg_complaint_rate);


--
-- Name: idx_program_stats_success; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_program_stats_success ON public.mv_program_stats USING btree (avg_success_rate);


--
-- Name: idx_risk_cache_card_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_risk_cache_card_id ON public.card_risk_cache USING btree (card_id);


--
-- Name: idx_risk_cache_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_risk_cache_risk ON public.card_risk_cache USING btree (risk);


--
-- Name: idx_risk_cache_updated; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_risk_cache_updated ON public.card_risk_cache USING btree (updated_at);


--
-- Name: idx_top10_card_id; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_top10_card_id ON public.top10_by_group USING btree (card_id);


--
-- Name: idx_top10_gz; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_top10_gz ON public.top10_by_group USING btree (gz);


--
-- Name: idx_top10_gz_rn; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_top10_gz_rn ON public.top10_by_group USING btree (gz, rn);


--
-- Name: idx_top10_risk; Type: INDEX; Schema: public; Owner: romannikitin
--

CREATE INDEX idx_top10_risk ON public.top10_by_group USING btree (risk);


--
-- Name: assignment_history assignment_history_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.assignment_history
    ADD CONSTRAINT assignment_history_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.card_assignments(assignment_id);


--
-- Name: assignment_history assignment_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.assignment_history
    ADD CONSTRAINT assignment_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(user_id);


--
-- Name: card_assignments card_assignments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romannikitin
--

ALTER TABLE ONLY public.card_assignments
    ADD CONSTRAINT card_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- PostgreSQL database dump complete
--

