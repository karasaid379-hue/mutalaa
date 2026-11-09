-- Sayfa eşlemesi: core, tefsir-elmalili, hadis-*, risale-dizin, mushaf-b (İçerik paketleri §3.2, §3.4, §3.5).
CREATE TABLE page_map (
  layout TEXT NOT NULL, volume INTEGER, page INTEGER NOT NULL, line INTEGER,
  start_anchor TEXT NOT NULL, start_offset INTEGER, end_anchor TEXT NOT NULL, end_offset INTEGER
);
CREATE INDEX page_map_page  ON page_map(layout, volume, page, line);
CREATE INDEX page_map_start ON page_map(start_anchor);
