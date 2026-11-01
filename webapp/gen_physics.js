// Fizika savollarini shablon asosida generatsiya qilish (uz/ru), mavzularga bo'lingan.
function genPhysicsBank(lang) {
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
      if (seen.has(key) || cand <= 0) continue;
      seen.add(key); out.push(cand);
    }
    while (out.length < n) out.push(correct + (out.length + 1) * (spread || 1));
    return out;
  }
  function add(topic, q, correct, dists, unit) {
    unit = unit || '';
    if (seenQ.has(q)) return;
    seenQ.add(q);
    const f = v => (fmt(v) + (unit ? (' ' + unit) : '')).trim();
    let opts = [f(correct)].concat(dists.map(f));
    opts = [...new Set(opts)];
    while (opts.length < 4) opts.push(f(correct + opts.length * 3 + 1));
    opts = opts.slice(0, 4);
    for (let i = opts.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[opts[i], opts[j]] = [opts[j], opts[i]]; }
    items.push({ topic: topic, q: q, options: opts, correct: f(correct) });
  }

  const T = lang === 'uz' ? {
    mex: "Mexanika: tezlik-masofa-vaqt", din: "Dinamika: F=ma", elek: "Elektr: Om qonuni",
    ish: "Ish va quvvat", zich: "Zichlik va bosim", issiq: "Issiqlik miqdori",
    opt: "Optika: linzalar", en: "Kinetik va potensial energiya"
  } : {
    mex: "Механика: скорость-путь-время", din: "Динамика: F=ma", elek: "Электричество: закон Ома",
    ish: "Работа и мощность", zich: "Плотность и давление", issiq: "Количество теплоты",
    opt: "Оптика: линзы", en: "Кинетическая и потенциальная энергия"
  };
  const TARGET = 180;

  // 1. Mexanika
  for (let i = 0; i < TARGET; i++) {
    const v = randInt(2, 120), t = randInt(2, 20), s = v * t;
    const mode = ['s', 'v', 't'][randInt(0, 2)];
    if (mode === 's') {
      const q = lang === 'uz' ? `Jism ${v} m/s tezlik bilan ${t} s harakatlansa, qancha masofa bosib o'tadi?` : `Тело движется со скоростью ${v} м/с в течение ${t} с. Какой путь оно пройдёт?`;
      add(T.mex, q, s, distract(s, Math.max(3, s * 0.2)), "m");
    } else if (mode === 'v') {
      const q = lang === 'uz' ? `Jism ${s} m masofani ${t} s da bosib o'tdi. Uning tezligi nechaga teng?` : `Тело прошло ${s} м за ${t} с. Чему равна его скорость?`;
      add(T.mex, q, v, distract(v, Math.max(2, v * 0.2)), "m/s");
    } else {
      const q = lang === 'uz' ? `Jism ${s} m masofani ${v} m/s tezlik bilan necha sekundda bosib o'tadi?` : `За сколько секунд тело пройдёт ${s} м со скоростью ${v} м/с?`;
      add(T.mex, q, t, distract(t, Math.max(1, t * 0.25)), "s");
    }
  }
  // 2. Dinamika
  for (let i = 0; i < TARGET; i++) {
    const m = randInt(1, 100), a = randInt(1, 20), F = m * a;
    const mode = ['F', 'm', 'a'][randInt(0, 2)];
    if (mode === 'F') {
      const q = lang === 'uz' ? `Massasi ${m} kg bo'lgan jismga ${a} m/s^2 tezlanish berish uchun qancha kuch kerak?` : `Какая сила нужна, чтобы придать телу массой ${m} кг ускорение ${a} м/с^2?`;
      add(T.din, q, F, distract(F, Math.max(3, F * 0.2)), "N");
    } else if (mode === 'm') {
      const q = lang === 'uz' ? `${F} N kuch ta'sirida jism ${a} m/s^2 tezlanish oldi. Jismning massasi nechaga teng?` : `Под действием силы ${F} Н тело получило ускорение ${a} м/с^2. Чему равна масса тела?`;
      add(T.din, q, m, distract(m, Math.max(2, m * 0.2)), "kg");
    } else {
      const q = lang === 'uz' ? `Massasi ${m} kg bo'lgan jismga ${F} N kuch ta'sir qilsa, tezlanishi nechaga teng?` : `На тело массой ${m} кг действует сила ${F} Н. Чему равно ускорение?`;
      add(T.din, q, a, distract(a, Math.max(1, a * 0.25)), "m/s^2");
    }
  }
  // 3. Elektr
  for (let i = 0; i < TARGET; i++) {
    const I = randInt(1, 20), R = randInt(1, 100), U = I * R;
    const mode = ['U', 'I', 'R'][randInt(0, 2)];
    if (mode === 'U') {
      const q = lang === 'uz' ? `Qarshiligi ${R} Om bo'lgan o'tkazgichdan ${I} A tok o'tsa, kuchlanish nechaga teng?` : `Через проводник сопротивлением ${R} Ом течёт ток ${I} А. Чему равно напряжение?`;
      add(T.elek, q, U, distract(U, Math.max(3, U * 0.2)), "V");
    } else if (mode === 'I') {
      const q = lang === 'uz' ? `Kuchlanishi ${U} V, qarshiligi ${R} Om bo'lgan zanjirda tok kuchi nechaga teng?` : `В цепи напряжением ${U} В и сопротивлением ${R} Ом найдите силу тока.`;
      add(T.elek, q, I, distract(I, Math.max(1, I * 0.25)), "A");
    } else {
      const q = lang === 'uz' ? `Kuchlanishi ${U} V, tok kuchi ${I} A bo'lgan o'tkazgichning qarshiligi nechaga teng?` : `Напряжение ${U} В, сила тока ${I} А. Чему равно сопротивление проводника?`;
      add(T.elek, q, R, distract(R, Math.max(2, R * 0.2)), "Ohm");
    }
  }
  // 4. Ish va quvvat
  for (let i = 0; i < TARGET; i++) {
    const F = randInt(5, 500), s = randInt(1, 50), A = F * s, t = randInt(1, 30);
    if (Math.random() < 0.5) {
      const q = lang === 'uz' ? `${F} N kuch jismni ${s} m masofaga siljitsa, bajarilgan ish nechaga teng?` : `Сила ${F} Н переместила тело на ${s} м. Чему равна совершённая работа?`;
      add(T.ish, q, A, distract(A, Math.max(3, A * 0.2)), "J");
    } else {
      const P = Math.round(A / t * 100) / 100;
      const q = lang === 'uz' ? `${A} J ish ${t} s da bajarilsa, quvvat nechaga teng?` : `Работа ${A} Дж совершена за ${t} с. Чему равна мощность?`;
      add(T.ish, q, P, distract(P, Math.max(2, P * 0.25)), "W");
    }
  }
  // 5. Zichlik va bosim
  for (let i = 0; i < TARGET; i++) {
    if (Math.random() < 0.5) {
      const m = randInt(10, 1000), V = randInt(2, 50), rho = Math.round(m / V * 100) / 100;
      const q = lang === 'uz' ? `Massasi ${m} kg, hajmi ${V} m^3 bo'lgan jismning zichligi nechaga teng?` : `Тело массой ${m} кг и объёмом ${V} м^3. Чему равна его плотность?`;
      add(T.zich, q, rho, distract(rho, Math.max(1, rho * 0.25)), "kg/m^3");
    } else {
      const F = randInt(10, 1000), S = randInt(1, 20), P = Math.round(F / S * 100) / 100;
      const q = lang === 'uz' ? `${F} N kuch ${S} m^2 yuzaga ta'sir qilsa, bosim nechaga teng?` : `Сила ${F} Н действует на площадь ${S} м^2. Чему равно давление?`;
      add(T.zich, q, P, distract(P, Math.max(1, P * 0.25)), "Pa");
    }
  }
  // 6. Issiqlik miqdori
  for (let i = 0; i < TARGET; i++) {
    const c = [4200, 2100, 900, 380, 130][randInt(0, 4)], m = randInt(1, 20), dT = randInt(5, 80), Q = c * m * dT;
    const q = lang === 'uz'
      ? `Solishtirma issiqlik sig'imi ${c} J/(kg·°C), massasi ${m} kg bo'lgan jismni ${dT}°C ga isitish uchun qancha issiqlik kerak?`
      : `Сколько теплоты нужно, чтобы нагреть тело массой ${m} кг (удельная теплоёмкость ${c} Дж/(кг·°C)) на ${dT}°C?`;
    add(T.issiq, q, Q, distract(Q, Math.max(100, Q * 0.2)), "J");
  }
  // 7. Optika
  for (let i = 0; i < TARGET; i++) {
    const F = randInt(1, 50), D = Math.round((1 / F) * 100) / 100;
    const q = lang === 'uz' ? `Fokus masofasi ${F} m bo'lgan linzaning optik kuchi nechaga teng?` : `Чему равна оптическая сила линзы с фокусным расстоянием ${F} м?`;
    add(T.opt, q, D, distract(D, Math.max(0.1, D * 0.3)), "dptr");
  }
  // 8. Energiya
  for (let i = 0; i < TARGET; i++) {
    if (Math.random() < 0.5) {
      const m = randInt(1, 100), v = randInt(1, 30), Ek = Math.round(0.5 * m * v * v * 10) / 10;
      const q = lang === 'uz' ? `Massasi ${m} kg, tezligi ${v} m/s bo'lgan jismning kinetik energiyasi nechaga teng?` : `Чему равна кинетическая энергия тела массой ${m} кг и скоростью ${v} м/с?`;
      add(T.en, q, Ek, distract(Ek, Math.max(5, Ek * 0.2)), "J");
    } else {
      const m = randInt(1, 100), h = randInt(1, 50), g = 10, Ep = m * g * h;
      const q = lang === 'uz' ? `Massasi ${m} kg bo'lgan jism ${h} m balandlikda. Uning potensial energiyasi nechaga teng? (g=10 m/s^2)` : `Тело массой ${m} кг находится на высоте ${h} м. Чему равна потенциальная энергия? (g=10 м/с^2)`;
      add(T.en, q, Ep, distract(Ep, Math.max(5, Ep * 0.2)), "J");
    }
  }
  return items;
}
