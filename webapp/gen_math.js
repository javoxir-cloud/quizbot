// Matematika savollarini shablon asosida generatsiya qilish (uz/ru), mavzularga bo'lingan.
function genMathBank(lang) {
  const items = [];
  const seenQ = new Set();
  function fmt(n) {
    if (typeof n === 'number' && !Number.isInteger(n)) return (Math.round(n * 100) / 100).toString();
    return n.toString();
  }
  function randInt(a, b) { return a + Math.floor(Math.random() * (b - a + 1)); }
  function distract(correct, spread, n) {
    n = n || 3;
    spread = spread || Math.max(1, Math.abs(correct) * 0.2, 2);
    const seen = new Set([Math.round(correct * 10000) / 10000]);
    const out = [];
    let tries = 0;
    while (out.length < n && tries < 50) {
      tries++;
      const delta = (Math.random() < 0.5 ? -1 : 1) * (spread * 0.3 + Math.random() * (spread * 1.5));
      const cand = correct + delta;
      const key = Math.round(cand * 10000) / 10000;
      if (seen.has(key)) continue;
      seen.add(key); out.push(cand);
    }
    while (out.length < n) out.push(correct + (out.length + 1) * (spread || 1));
    return out;
  }
  function add(topic, q, correct, dists) {
    if (seenQ.has(q)) return;
    seenQ.add(q);
    let opts = [fmt(correct)].concat(dists.map(fmt));
    opts = [...new Set(opts)];
    while (opts.length < 4) opts.push(fmt(correct + opts.length * 3 + 1));
    opts = opts.slice(0, 4);
    for (let i = opts.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[opts[i], opts[j]] = [opts[j], opts[i]]; }
    items.push({ topic: topic, q: q, options: opts, correct: fmt(correct) });
  }

  const T = lang === 'uz' ? {
    arif: "Arifmetik amallar", foiz: "Foizlar", chiz: "Chiziqli tenglamalar",
    kvad: "Kvadrat tenglamalar", perim: "Geometriya: perimetr va yuza", hajm: "Geometriya: hajm",
    prog: "Progressiyalar", daraja: "Darajalar va ildizlar", nisbat: "Nisbat va ulush", stat: "Statistika: o'rtacha qiymat"
  } : {
    arif: "Арифметические действия", foiz: "Проценты", chiz: "Линейные уравнения",
    kvad: "Квадратные уравнения", perim: "Периметр и площадь", hajm: "Объём фигур",
    prog: "Прогрессии", daraja: "Степени и корни", nisbat: "Отношение и доли", stat: "Статистика: среднее значение"
  };
  const TARGET = 180;

  // 1. Arifmetik amallar
  for (let i = 0; i < TARGET; i++) {
    const op = ['+', '-', '*', '/'][randInt(0, 3)];
    let a, b, c;
    if (op === '/') { b = randInt(2, 20); const res = randInt(2, 50); a = b * res; c = a / b; }
    else if (op === '+') { a = randInt(10, 999); b = randInt(2, 999); c = a + b; }
    else if (op === '-') { a = randInt(10, 999); b = randInt(2, 999); if (b > a) [a, b] = [b, a]; c = a - b; }
    else { a = randInt(2, 99); b = randInt(2, 99); c = a * b; }
    const q = `${a} ${op} ${b} = ?`;
    add(T.arif, q, c, distract(c, Math.max(3, Math.abs(c) * 0.15)));
  }
  // 2. Foizlar
  for (let i = 0; i < TARGET; i++) {
    const base = randInt(20, 2000);
    const pct = [5, 10, 12, 15, 20, 25, 30, 40, 45, 50, 60, 75][randInt(0, 11)];
    const val = Math.round(base * pct / 100 * 100) / 100;
    const q = lang === 'uz' ? `${base} ning ${pct}%i nechaga teng?` : `Чему равно ${pct}% от ${base}?`;
    add(T.foiz, q, val, distract(val, Math.max(2, val * 0.25)));
  }
  // 3. Chiziqli tenglamalar
  for (let i = 0; i < TARGET; i++) {
    const x = randInt(-20, 20), a = randInt(2, 15), b = randInt(-50, 50);
    const c = a * x + b;
    const sign = b >= 0 ? '+' : '-';
    const q = lang === 'uz' ? `${a}x ${sign} ${Math.abs(b)} = ${c} tenglamani yeching: x = ?` : `Решите уравнение: ${a}x ${sign} ${Math.abs(b)} = ${c}. x = ?`;
    add(T.chiz, q, x, distract(x, Math.max(2, Math.abs(x) * 0.4 + 2)));
  }
  // 4. Kvadrat tenglamalar
  for (let i = 0; i < TARGET; i++) {
    let r1 = randInt(-10, 10), r2 = randInt(-10, 10);
    if (r1 === r2) r2 = r1 + 1;
    const b = -(r1 + r2), c = r1 * r2;
    const bsign = b >= 0 ? '+' : '-', csign = c >= 0 ? '+' : '-';
    const q = lang === 'uz'
      ? `x^2 ${bsign} ${Math.abs(b)}x ${csign} ${Math.abs(c)} = 0 tenglamaning ildizlaridan biri qaysi?`
      : `Один из корней уравнения x^2 ${bsign} ${Math.abs(b)}x ${csign} ${Math.abs(c)} = 0?`;
    const correct = Math.max(r1, r2), wrong = Math.min(r1, r2);
    add(T.kvad, q, correct, [wrong, correct + 1, correct - 1]);
  }
  // 5. Geometriya: perimetr va yuza
  for (let i = 0; i < TARGET; i++) {
    const shape = ['rect', 'square', 'triangle', 'circle'][randInt(0, 3)];
    if (shape === 'rect') {
      const a = randInt(3, 40), b = randInt(3, 40), s = a * b;
      const q = lang === 'uz' ? `Tomonlari ${a} sm va ${b} sm bo'lgan to'g'ri to'rtburchakning yuzi nechaga teng?` : `Чему равна площадь прямоугольника со сторонами ${a} см и ${b} см?`;
      add(T.perim, q, s, distract(s, Math.max(3, s * 0.2)));
    } else if (shape === 'square') {
      const a = randInt(3, 40), p = a * 4;
      const q = lang === 'uz' ? `Tomoni ${a} sm bo'lgan kvadratning perimetri nechaga teng?` : `Чему равен периметр квадрата со стороной ${a} см?`;
      add(T.perim, q, p, distract(p, Math.max(3, p * 0.2)));
    } else if (shape === 'triangle') {
      const base = randInt(4, 40), height = randInt(3, 30), area = base * height / 2;
      const q = lang === 'uz' ? `Asosi ${base} sm va balandligi ${height} sm bo'lgan uchburchakning yuzi nechaga teng?` : `Чему равна площадь треугольника с основанием ${base} см и высотой ${height} см?`;
      add(T.perim, q, area, distract(area, Math.max(3, area * 0.2)));
    } else {
      const r = randInt(2, 25), area = Math.round(3.14 * r * r * 10) / 10;
      const q = lang === 'uz' ? `Radiusi ${r} sm bo'lgan doiraning yuzi taqriban nechaga teng? (π≈3.14)` : `Чему приблизительно равна площадь круга радиусом ${r} см? (π≈3.14)`;
      add(T.perim, q, area, distract(area, Math.max(3, area * 0.2)));
    }
  }
  // 6. Geometriya: hajm
  for (let i = 0; i < TARGET; i++) {
    const shape = ['cube', 'box', 'cylinder'][randInt(0, 2)];
    let q, v;
    if (shape === 'cube') {
      const a = randInt(2, 20); v = a ** 3;
      q = lang === 'uz' ? `Qirrasi ${a} sm bo'lgan kubning hajmi nechaga teng?` : `Чему равен объём куба с ребром ${a} см?`;
    } else if (shape === 'box') {
      const a = randInt(2, 20), b = randInt(2, 20), c = randInt(2, 20); v = a * b * c;
      q = lang === 'uz' ? `O'lchamlari ${a}×${b}×${c} sm bo'lgan to'g'ri burchakli parallelepipedning hajmi nechaga teng?` : `Чему равен объём прямоугольного параллелепипеда ${a}×${b}×${c} см?`;
    } else {
      const r = randInt(2, 15), h = randInt(3, 25); v = Math.round(3.14 * r * r * h * 10) / 10;
      q = lang === 'uz' ? `Radiusi ${r} sm, balandligi ${h} sm bo'lgan silindrning hajmi taqriban nechaga teng? (π≈3.14)` : `Чему приблизительно равен объём цилиндра радиусом ${r} см и высотой ${h} см? (π≈3.14)`;
    }
    add(T.hajm, q, v, distract(v, Math.max(3, v * 0.2)));
  }
  // 7. Progressiyalar
  for (let i = 0; i < TARGET; i++) {
    if (Math.random() < 0.5) {
      const a1 = randInt(-20, 20); let d = randInt(-10, 10); if (d === 0) d = 1;
      const n = randInt(4, 15), an = a1 + (n - 1) * d;
      const q = lang === 'uz' ? `Arifmetik progressiyada a1=${a1}, d=${d}. a${n} hadni toping.` : `В арифметической прогрессии a1=${a1}, d=${d}. Найдите a${n}.`;
      add(T.prog, q, an, distract(an, Math.max(2, Math.abs(d) * 2 + 1)));
    } else {
      const b1 = randInt(1, 5), qr = randInt(2, 3), n = randInt(3, 6), bn = b1 * (qr ** (n - 1));
      const q = lang === 'uz' ? `Geometrik progressiyada b1=${b1}, q=${qr}. b${n} hadni toping.` : `В геометрической прогрессии b1=${b1}, q=${qr}. Найдите b${n}.`;
      add(T.prog, q, bn, distract(bn, Math.max(3, bn * 0.3)));
    }
  }
  // 8. Darajalar va ildizlar
  for (let i = 0; i < TARGET; i++) {
    const kind = ['power', 'sqrt', 'cbrt'][randInt(0, 2)];
    let q, val;
    if (kind === 'power') {
      const base = randInt(2, 12), exp = randInt(2, 4); val = base ** exp;
      q = lang === 'uz' ? `${base}^${exp} nechaga teng?` : `Чему равно ${base}^${exp}?`;
    } else if (kind === 'sqrt') {
      const root = randInt(2, 20); val = root; const v2 = root * root;
      q = lang === 'uz' ? `√${v2} nechaga teng?` : `Чему равен √${v2}?`;
    } else {
      const root = randInt(2, 10); val = root; const v3 = root ** 3;
      q = lang === 'uz' ? `∛${v3} nechaga teng?` : `Чему равен ∛${v3}?`;
    }
    add(T.daraja, q, val, distract(val, Math.max(2, val * 0.3 + 1)));
  }
  // 9. Nisbat va ulush
  for (let i = 0; i < TARGET; i++) {
    const total = randInt(20, 500), parts = randInt(2, 8), share = randInt(1, parts - 1);
    const val = Math.round(total * share / parts * 100) / 100;
    const q = lang === 'uz' ? `${total} sonini ${parts} ulushga bo'lib, ${share} ulushi nechaga teng ekanini toping.` : `Разделите ${total} на ${parts} долей и найдите, чему равна ${share} доля(и).`;
    add(T.nisbat, q, val, distract(val, Math.max(2, val * 0.25)));
  }
  // 10. Statistika: o'rtacha qiymat
  for (let i = 0; i < TARGET; i++) {
    const n = randInt(3, 6);
    const nums = Array.from({ length: n }, () => randInt(1, 100));
    const avg = Math.round(nums.reduce((a, b) => a + b, 0) / n * 100) / 100;
    const q = lang === 'uz' ? `${nums.join(", ")} sonlarining o'rtacha arifmetigi nechaga teng?` : `Чему равно среднее арифметическое чисел ${nums.join(", ")}?`;
    add(T.stat, q, avg, distract(avg, Math.max(2, avg * 0.25)));
  }
  return items;
}
