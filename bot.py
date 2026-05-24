create table products (
  id bigint primary key generated always as identity,
  name text,
  brand text,
  category text,
  price integer,
  old_price integer,
  size text,
  badge text,
  description text,
  icon text,
  photo_url text,
  file_id text,
  created_at timestamp default now()
);

alter table products enable row level security;

create policy "Public read" on products for select using (true);
create policy "Service insert" on products for insert with check (true);
create policy "Service delete" on products for delete using (true);
