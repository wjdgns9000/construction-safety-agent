'use strict';

const PptxGenJS = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

// ── CLI args ──────────────────────────────────────────────────────────────────
function parseArgs() {
  const a = {};
  process.argv.slice(2).forEach((v, i, arr) => {
    if (v === '--input')  a.input  = arr[i + 1];
    if (v === '--output') a.output = arr[i + 1];
  });
  if (!a.input || !a.output) {
    console.error('Usage: node build_ppt.js --input <path> --output <path>');
    process.exit(1);
  }
  return a;
}

// ── Design tokens ─────────────────────────────────────────────────────────────
const FONT = '맑은 고딕';
const C = {
  headerBg : '1A365D',
  white    : 'FFFFFF',
  body     : '1A202C',
  sub      : '718096',
  light    : 'EDF2F7',
  divider  : 'CBD5E0',
  accent   : '2B6CB0',
};

const TYPE_LABELS = {
  fall: '추락', collapse: '붕괴·도괴', falling_object: '낙하물',
  electrocution: '감전', caught_in: '끼임·협착', fire: '화재·폭발',
  collision: '충돌·접촉', other: '기타',
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function svgB64(iconPath) {
  if (!iconPath) return null;
  const full = path.resolve(iconPath);
  if (!fs.existsSync(full)) return null;
  return 'data:image/svg+xml;base64,' + fs.readFileSync(full).toString('base64');
}

function iconB64ForType(type) {
  return svgB64(path.join('assets', 'icons', `${type || 'other'}.svg`));
}

function getWeekLabel(data) {
  const dates = data.map(d => d.accident_date || d.collected_at || '').filter(Boolean).sort();
  if (!dates.length) return '';
  const d = new Date(dates[dates.length - 1]);
  if (isNaN(d)) return '';
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${Math.ceil(d.getDate() / 7)}주차`;
}

function buildGroups(data) {
  const map = {};
  for (const item of data) {
    const t = item.type || 'other';
    if (!map[t]) {
      map[t] = {
        type: t,
        label: item.type_label || TYPE_LABELS[t] || t,
        color: (item.icon_color || '#718096').replace('#', ''),
        toc_order: item.toc_order ?? 99,
        items: [],
      };
    }
    map[t].items.push(item);
  }
  return Object.values(map).sort((a, b) => a.toc_order - b.toc_order || b.items.length - a.items.length);
}

// ── Slide builders ────────────────────────────────────────────────────────────
function addCoverSlide(pptx, data) {
  const slide = pptx.addSlide();
  const label = getWeekLabel(data);
  const today = new Date().toLocaleDateString('ko-KR');

  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 3.5, fill: { color: C.headerBg } });

  slide.addText('건설업 사고사례 보고서', {
    x: 0.5, y: 0.9, w: 9, h: 1.1,
    fontSize: 32, bold: true, color: C.white, fontFace: FONT, align: 'center', valign: 'middle',
  });

  slide.addText(`${label}  |  수집 ${data.length}건`, {
    x: 0.5, y: 2.1, w: 9, h: 0.7,
    fontSize: 16, color: 'CBD5E0', fontFace: FONT, align: 'center',
  });

  slide.addText(`생성일: ${today}`, {
    x: 0.5, y: 4.2, w: 9, h: 0.5,
    fontSize: 13, color: C.body, fontFace: FONT, align: 'center',
  });

  slide.addText('출처: KOSHA 한국산업안전보건공단', {
    x: 0.5, y: 6.6, w: 9, h: 0.5,
    fontSize: 11, color: C.sub, fontFace: FONT, align: 'center',
  });
}

function addTocSlide(pptx, groups, data) {
  const slide = pptx.addSlide();

  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 1.1, fill: { color: C.headerBg } });
  slide.addText('목차', {
    x: 0.4, y: 0, w: 9.2, h: 1.1,
    fontSize: 22, bold: true, color: C.white, fontFace: FONT, valign: 'middle',
  });

  slide.addText(`총 ${data.length}건 수집 · ${data.length}건 분석 완료`, {
    x: 0.5, y: 1.3, w: 9, h: 0.45,
    fontSize: 13, color: C.sub, fontFace: FONT,
  });

  const startY = 1.9;
  const lineH = 0.55;
  groups.forEach((g, i) => {
    const y = startY + i * lineH;
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.5, y: y + 0.12, w: 0.18, h: 0.28,
      fill: { color: g.color },
    });
    slide.addText(`${String(i + 1).padStart(2, '0')}  ${g.label}`, {
      x: 0.85, y, w: 5, h: lineH,
      fontSize: 14, color: C.body, fontFace: FONT, bold: true,
    });
    slide.addText(`${g.items.length}건`, {
      x: 6, y, w: 3.6, h: lineH,
      fontSize: 14, color: g.color, fontFace: FONT, bold: true, align: 'right',
    });
  });
}

function addSectionSlide(pptx, group) {
  const slide = pptx.addSlide();

  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 4.5, fill: { color: group.color } });

  const img = iconB64ForType(group.type);
  if (img) slide.addImage({ data: img, x: 3.8, y: 0.6, w: 2.4, h: 2.4 });

  slide.addText(group.label, {
    x: 0.5, y: 3.2, w: 9, h: 0.95,
    fontSize: 34, bold: true, color: C.white, fontFace: FONT, align: 'center',
  });
  slide.addText(`${group.items.length}건`, {
    x: 0.5, y: 4.9, w: 9, h: 0.7,
    fontSize: 22, color: C.body, fontFace: FONT, align: 'center',
  });
}

function addAccidentSlide(pptx, item) {
  const slide = pptx.addSlide();
  const type = item.type || 'other';
  const colorHex = (item.icon_color || '#718096').replace('#', '');
  const img = iconB64ForType(type);

  // 헤더
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 1.25, fill: { color: C.headerBg } });
  if (img) slide.addImage({ data: img, x: 0.15, y: 0.15, w: 0.9, h: 0.9 });

  slide.addText(item.keyword || '(제목 없음)', {
    x: 1.2, y: 0.05, w: 8.6, h: 0.68,
    fontSize: 17, bold: true, color: C.white, fontFace: FONT, valign: 'bottom',
    charSpacing: 0.5,
  });

  const dateLocation = [item.accident_date, item.location].filter(Boolean).join('  |  ');
  slide.addText(dateLocation || ' ', {
    x: 1.2, y: 0.78, w: 8.6, h: 0.4,
    fontSize: 11, color: 'A0AEC0', fontFace: FONT,
  });

  // 왼쪽 패널 (아이콘)
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 1.25, w: 3.2, h: 5.35,
    fill: { color: 'F7FAFC' },
    line: { color: C.divider, width: 0.5 },
  });
  if (img) slide.addImage({ data: img, x: 0.35, y: 2.05, w: 2.5, h: 2.5 });

  // 오른쪽 패널
  const RX = 3.35;
  const RW = 6.45;

  slide.addText('발생경위', {
    x: RX, y: 1.3, w: RW, h: 0.32,
    fontSize: 10, bold: true, color: C.accent, fontFace: FONT,
  });
  slide.addText(item.summary_200 || item.contents || '(경위 정보 없음)', {
    x: RX, y: 1.62, w: RW, h: 1.5,
    fontSize: 11.5, color: C.body, fontFace: FONT, wrap: true, valign: 'top',
  });

  // 구분선 (얇은 rect)
  slide.addShape(pptx.ShapeType.rect, {
    x: RX, y: 3.18, w: RW, h: 0.02,
    fill: { color: C.divider },
  });

  slide.addText('원인', {
    x: RX, y: 3.25, w: RW, h: 0.3,
    fontSize: 10, bold: true, color: C.accent, fontFace: FONT,
  });
  const causes = (item.causes || []).slice(0, 3);
  const causeText = causes.map((c, i) => `${'①②③'[i]}  ${c}`).join('    ');
  slide.addText(causeText || '—', {
    x: RX, y: 3.56, w: RW, h: 0.55,
    fontSize: 11, color: C.body, fontFace: FONT, wrap: true,
  });

  slide.addShape(pptx.ShapeType.rect, {
    x: RX, y: 4.16, w: RW, h: 0.02,
    fill: { color: C.divider },
  });

  slide.addText('예방대책', {
    x: RX, y: 4.23, w: RW, h: 0.3,
    fontSize: 10, bold: true, color: C.accent, fontFace: FONT,
  });
  const preventions = (item.preventions || []).slice(0, 3);
  const prevText = preventions.map((p, i) => `${'①②③'[i]}  ${p}`).join('    ');
  slide.addText(prevText || '—', {
    x: RX, y: 4.54, w: RW, h: 0.9,
    fontSize: 11, color: C.body, fontFace: FONT, wrap: true,
  });

  // 푸터
  slide.addShape(pptx.ShapeType.rect, {
    x: 0, y: 6.6, w: 10, h: 0.9,
    fill: { color: C.light },
  });
  const lawRefs = (item.law_refs || []).join('  ·  ');
  slide.addText(`관련법령:  ${lawRefs || '—'}`, {
    x: 0.25, y: 6.62, w: 9.5, h: 0.86,
    fontSize: 10, color: C.sub, fontFace: FONT, valign: 'middle',
  });
}

function addSourceSlide(pptx, data) {
  const slide = pptx.addSlide();

  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 1.1, fill: { color: C.headerBg } });
  slide.addText('데이터 출처', {
    x: 0.4, y: 0, w: 9.2, h: 1.1,
    fontSize: 22, bold: true, color: C.white, fontFace: FONT, valign: 'middle',
  });

  slide.addText('■  KOSHA 한국산업안전보건공단', {
    x: 0.5, y: 1.35, w: 9, h: 0.45,
    fontSize: 13, bold: true, color: C.body, fontFace: FONT,
  });
  slide.addText('https://www.kosha.or.kr/kosha/data/accidentCaseBoard.do', {
    x: 0.75, y: 1.8, w: 9, h: 0.38,
    fontSize: 11, color: C.accent, fontFace: FONT,
  });

  slide.addText('■  Naver 뉴스 RSS', {
    x: 0.5, y: 2.45, w: 9, h: 0.45,
    fontSize: 13, bold: true, color: C.body, fontFace: FONT,
  });
  slide.addText('https://search.naver.com/rss.naver?query=건설+안전사고', {
    x: 0.75, y: 2.9, w: 9, h: 0.38,
    fontSize: 11, color: C.accent, fontFace: FONT,
  });

  const now = new Date().toLocaleString('ko-KR');
  slide.addText(`생성일시: ${now}\n시스템: 건설안전 에이전트 (Claude Code 기반)`, {
    x: 0.5, y: 6.2, w: 9, h: 0.9,
    fontSize: 10, color: C.sub, fontFace: FONT,
  });
}

// ── Main ──────────────────────────────────────────────────────────────────────
const args = parseArgs();
const data = JSON.parse(fs.readFileSync(args.input, 'utf-8'));
const groups = buildGroups(data);

const pptx = new PptxGenJS();

const outDir = path.dirname(path.resolve(args.output));
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

addCoverSlide(pptx, data);
addTocSlide(pptx, groups, data);
for (const group of groups) {
  addSectionSlide(pptx, group);
  for (const item of group.items) {
    addAccidentSlide(pptx, item);
  }
}
addSourceSlide(pptx, data);

pptx.writeFile({ fileName: path.resolve(args.output) })
  .then(() => {
    const total = 2 + groups.length + data.length + 1;
    console.log(`[PPT] 완료: ${args.output} (${total}슬라이드)`);
  })
  .catch(err => { console.error(`[PPT] 실패: ${err}`); process.exit(1); });
