---
name: db-schema
description: FridgeTube DB 스키마. DBA와 Backend 에이전트가 사용.
---

# DB 스키마 (12 테이블)

## 1. users
- id UUID PK
- email VARCHAR(255) UNIQUE NULL
- nickname VARCHAR(50) NOT NULL
- provider VARCHAR(20) NOT NULL ('google'/'kakao'/'anonymous')
- provider_id VARCHAR(255)
- default_servings INT DEFAULT 2
- created_at, updated_at TIMESTAMP

## 2. youtube_channels
- id UUID PK
- channel_id VARCHAR(50) UNIQUE NOT NULL (YouTube 원본 ID)
- channel_name VARCHAR(200) NOT NULL
- thumbnail_url TEXT
- subscriber_count BIGINT
- synced_at TIMESTAMP

## 3. user_favorite_channels
- id UUID PK
- user_id FK→users
- channel_id FK→youtube_channels
- priority INT DEFAULT 0
- UNIQUE(user_id, channel_id)

## 4. user_ingredients
- id UUID PK
- user_id FK→users
- ingredient_id FK→ingredient_master NULL
- name VARCHAR(100) NOT NULL
- amount FLOAT NULL (미입력=양 모름)
- unit VARCHAR(20) NULL
- source VARCHAR(20) DEFAULT 'manual' ('manual'/'photo')
- created_at, updated_at

## 5. ingredient_master
- id UUID PK
- name VARCHAR(100) NOT NULL
- aliases TEXT[] (별칭 배열)
- category VARCHAR(50) NOT NULL ('채소'/'육류'/'해산물'/'양념'/'유제품'/'기타')
- default_unit VARCHAR(20)
- INDEX: GIN(aliases), GIN(name gin_trgm_ops)

## 6. dish_name_master
- id UUID PK
- name VARCHAR(200) NOT NULL
- aliases TEXT[]
- cuisine_type VARCHAR(20) NOT NULL ('한식'/'중식'/'양식'/'일식'/'동남아'/'퓨전')
- pattern_suffix VARCHAR(20) ('찌개','볶음','탕','파스타' 등)
- typical_ingredients TEXT[] (표시용)
- typical_ingredient_ids UUID[] (ingredient_master FK 배열, 매칭용)
- popularity_score FLOAT DEFAULT 0
- INDEX: GIN(aliases), GIN(name gin_trgm_ops), GIN(typical_ingredient_ids)

## 7. channel_video_index ⚠️ YouTube 데이터 30일 TTL
- id UUID PK
- channel_id FK→youtube_channels
- video_id VARCHAR(20) UNIQUE NOT NULL
- title VARCHAR(500) NOT NULL
- description_text TEXT
- has_recipe_in_desc BOOLEAN DEFAULT false
- published_at TIMESTAMP
- tsv_title TSVECTOR (GIN 인덱스)
- tsv_description TSVECTOR (GIN 인덱스)
- indexed_at TIMESTAMP NOT NULL
- expires_at TIMESTAMP NOT NULL (indexed_at + 30일)
- INDEX: GIN(tsv_title), GIN(tsv_description), idx(expires_at), GIN(title gin_trgm_ops)

## 8. youtube_video_snapshot ⚠️ YouTube 데이터 30일 TTL
- id UUID PK
- video_id VARCHAR(20) UNIQUE NOT NULL
- title VARCHAR(500) NOT NULL
- yt_channel_id VARCHAR(50)
- channel_name VARCHAR(200)
- view_count BIGINT
- like_count BIGINT
- duration_seconds INT
- thumbnail_url TEXT
- published_at TIMESTAMP
- fetched_at TIMESTAMP NOT NULL
- expires_at TIMESTAMP NOT NULL (fetched_at + 30일)

## 9. recipe_core (추출 레시피 — 장기 보관)
- id UUID PK
- source_type VARCHAR(20) NOT NULL ('youtube'/'text'/'ocr'/'url')
- source_id VARCHAR(100) NOT NULL
- UNIQUE(source_type, source_id)
- dish_name VARCHAR(200) NOT NULL
- base_servings INT NOT NULL
- base_servings_source VARCHAR(20) DEFAULT 'default' ('explicit'/'inferred'/'default')
- steps JSONB NOT NULL
- cooking_time_min INT
- difficulty VARCHAR(10) ('easy'/'medium'/'hard')
- raw_transcript TEXT
- confidence_score FLOAT
- prompt_version VARCHAR(20)
- created_at TIMESTAMP

## 10. recipe_core_ingredients
- id UUID PK
- recipe_id FK→recipe_core
- ingredient_id FK→ingredient_master NULL
- raw_name VARCHAR(200) NOT NULL
- name VARCHAR(100) NOT NULL
- amount FLOAT
- unit VARCHAR(20)
- scaling_strategy VARCHAR(20) DEFAULT 'linear' ('linear'/'stepwise'/'to_taste'/'fixed')
- is_optional BOOLEAN DEFAULT false
- sort_order INT

## 11. search_history
- id UUID PK
- user_id FK→users NULL
- session_id VARCHAR(100)
- query TEXT NOT NULL
- search_type VARCHAR(20) NOT NULL ('dish_name'/'ingredients'/'ambiguous')
- detected_dish_id FK→dish_name_master NULL
- detected_ingredients TEXT[] NULL
- servings INT
- mode VARCHAR(20) ('video'/'recipe')
- channel_filter BOOLEAN DEFAULT false
- created_at TIMESTAMP

## 12. saved_recipes
- id UUID PK
- user_id FK→users
- recipe_core_id FK→recipe_core
- custom_servings INT
- notes TEXT
- created_at TIMESTAMP

## 필수 인덱스
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- tsvector
CREATE INDEX idx_cvi_tsv_title ON channel_video_index USING GIN(tsv_title);
CREATE INDEX idx_cvi_tsv_desc ON channel_video_index USING GIN(tsv_description);
-- trgm fuzzy
CREATE INDEX idx_cvi_title_trgm ON channel_video_index USING GIN(title gin_trgm_ops);
CREATE INDEX idx_dish_name_trgm ON dish_name_master USING GIN(name gin_trgm_ops);
CREATE INDEX idx_ingredient_name_trgm ON ingredient_master USING GIN(name gin_trgm_ops);
-- TTL
CREATE INDEX idx_cvi_expires ON channel_video_index(expires_at);
CREATE INDEX idx_snapshot_expires ON youtube_video_snapshot(expires_at);
-- 기타
CREATE UNIQUE INDEX idx_recipe_core_source ON recipe_core(source_type, source_id);
CREATE INDEX idx_user_ingredients_user ON user_ingredients(user_id);
CREATE INDEX idx_search_history_user ON search_history(user_id, created_at DESC);
```
