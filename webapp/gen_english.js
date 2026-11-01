// Ingliz tili savollarini generatsiya qilish. mode: 'uz' (savol o'zbekcha, javob inglizcha),
// 'ru' (savol ruscha), 'en' (hammasi inglizcha - sinonim/ta'rif asosida).
const EN_WORDS = [
  // [english, uzbek, russian, category]
  ["mother","ona","мать","Oila"], ["father","ota","отец","Oila"], ["sister","opa-singil","сестра","Oila"],
  ["brother","aka-uka","брат","Oila"], ["son","o'g'il","сын","Oila"], ["daughter","qiz","дочь","Oila"],
  ["grandmother","buvi","бабушка","Oila"], ["grandfather","bobo","дедушка","Oila"], ["family","oila","семья","Oila"],
  ["child","bola","ребёнок","Oila"], ["parents","ota-ona","родители","Oila"], ["wife","xotin","жена","Oila"],
  ["husband","er","муж","Oila"],
  ["bread","non","хлеб","Ovqat"], ["water","suv","вода","Ovqat"], ["milk","sut","молоко","Ovqat"],
  ["meat","go'sht","мясо","Ovqat"], ["rice","guruch","рис","Ovqat"], ["apple","olma","яблоко","Ovqat"],
  ["banana","banan","банан","Ovqat"], ["tea","choy","чай","Ovqat"], ["sugar","shakar","сахар","Ovqat"],
  ["salt","tuz","соль","Ovqat"], ["egg","tuxum","яйцо","Ovqat"], ["cheese","pishloq","сыр","Ovqat"],
  ["soup","sho'rva","суп","Ovqat"], ["fish","baliq","рыба","Ovqat"], ["potato","kartoshka","картофель","Ovqat"],
  ["onion","piyoz","лук","Ovqat"],
  ["dog","it","собака","Hayvonlar"], ["cat","mushuk","кошка","Hayvonlar"], ["horse","ot","лошадь","Hayvonlar"],
  ["cow","sigir","корова","Hayvonlar"], ["bird","qush","птица","Hayvonlar"], ["sheep","qo'y","овца","Hayvonlar"],
  ["lion","sher","лев","Hayvonlar"], ["elephant","fil","слон","Hayvonlar"], ["fox","tulki","лиса","Hayvonlar"],
  ["wolf","bo'ri","волк","Hayvonlar"], ["rabbit","quyon","кролик","Hayvonlar"], ["bear","ayiq","медведь","Hayvonlar"],
  ["red","qizil","красный","Ranglar"], ["blue","ko'k","синий","Ranglar"], ["green","yashil","зелёный","Ranglar"],
  ["yellow","sariq","жёлтый","Ranglar"], ["black","qora","чёрный","Ranglar"], ["white","oq","белый","Ranglar"],
  ["orange","to'q sariq","оранжевый","Ranglar"], ["purple","binafsha","фиолетовый","Ranglar"], ["pink","pushti","розовый","Ranglar"],
  ["brown","jigarrang","коричневый","Ranglar"], ["gray","kulrang","серый","Ranglar"],
  ["teacher","o'qituvchi","учитель","Kasblar"], ["doctor","shifokor","врач","Kasblar"], ["engineer","muhandis","инженер","Kasblar"],
  ["driver","haydovchi","водитель","Kasblar"], ["cook","oshpaz","повар","Kasblar"], ["worker","ishchi","рабочий","Kasblar"],
  ["farmer","dehqon","фермер","Kasblar"], ["lawyer","advokat","адвокат","Kasblar"], ["nurse","hamshira","медсестра","Kasblar"],
  ["pilot","uchuvchi","пилот","Kasblar"], ["singer","qo'shiqchi","певец","Kasblar"], ["writer","yozuvchi","писатель","Kasblar"],
  ["sun","quyosh","солнце","Tabiat"], ["moon","oy","луна","Tabiat"], ["star","yulduz","звезда","Tabiat"],
  ["sky","osmon","небо","Tabiat"], ["mountain","tog'","гора","Tabiat"], ["river","daryo","река","Tabiat"],
  ["sea","dengiz","море","Tabiat"], ["forest","o'rmon","лес","Tabiat"], ["tree","daraxt","дерево","Tabiat"],
  ["flower","gul","цветок","Tabiat"], ["rain","yomg'ir","дождь","Tabiat"], ["snow","qor","снег","Tabiat"],
  ["wind","shamol","ветер","Tabiat"], ["stone","tosh","камень","Tabiat"], ["earth","yer","земля","Tabiat"],
  ["table","stol","стол","Uy jihozlari"], ["chair","stul","стул","Uy jihozlari"], ["bed","karavot","кровать","Uy jihozlari"],
  ["window","deraza","окно","Uy jihozlari"], ["door","eshik","дверь","Uy jihozlari"], ["book","kitob","книга","Uy jihozlari"],
  ["pen","ruchka","ручка","Uy jihozlari"], ["lamp","chiroq","лампа","Uy jihozlari"], ["clock","soat","часы","Uy jihozlari"],
  ["mirror","oyna","зеркало","Uy jihozlari"], ["key","kalit","ключ","Uy jihozlари"], ["bag","sumka","сумка","Uy jihozlari"],
  ["run","yugurmoq","бегать","Fe'llar"], ["jump","sakramoq","прыгать","Fe'llar"], ["read","o'qimoq","читать","Fe'llar"],
  ["write","yozmoq","писать","Fe'llar"], ["speak","gapirmoq","говорить","Fe'llar"], ["listen","eshitmoq","слушать","Fe'llar"],
  ["eat","yemoq","есть","Fe'llar"], ["drink","ichmoq","пить","Fe'llar"], ["sleep","uxlamoq","спать","Fe'llar"],
  ["work","ishlamoq","работать","Fe'llar"], ["play","o'ynamoq","играть","Fe'llar"], ["swim","suzmoq","плавать","Fe'llar"],
  ["cook","pishirmoq","готовить","Fe'llar"], ["buy","sotib olmoq","покупать","Fe'llar"], ["sell","sotmoq","продавать","Fe'llar"],
  ["help","yordam bermoq","помогать","Fe'llar"], ["learn","o'rganmoq","учиться","Fe'llar"], ["teach","o'qitmoq","учить","Fe'llar"],
  ["big","katta","большой","Sifatlar"], ["small","kichik","маленький","Sifatlar"], ["fast","tez","быстрый","Sifatlar"],
  ["slow","sekin","медленный","Sifatlar"], ["happy","baxtli","счастливый","Sifatlar"], ["sad","xafa","грустный","Sifatlar"],
  ["beautiful","chiroyli","красивый","Sifatlar"], ["old","eski","старый","Sifatlar"], ["new","yangi","новый","Sifatlar"],
  ["strong","kuchli","сильный","Sifatlar"], ["weak","kuchsiz","слабый","Sifatlar"], ["clean","toza","чистый","Sifatlar"],
  ["one","bir","один","Raqamlar"], ["two","ikki","два","Raqamlar"], ["three","uch","три","Raqamlar"],
  ["four","to'rt","четыре","Raqamlar"], ["five","besh","пять","Raqamlar"], ["six","olti","шесть","Raqamlar"],
  ["seven","yetti","семь","Raqamlar"], ["eight","sakkiz","восемь","Raqamlar"], ["nine","to'qqiz","девять","Raqamlar"],
  ["ten","o'n","десять","Raqamlar"], ["hundred","yuz","сто","Raqamlar"], ["thousand","ming","тысяча","Raqamlar"],
  ["Monday","dushanba","понедельник","Hafta kunlari"], ["Tuesday","seshanba","вторник","Hafta kunlari"],
  ["Wednesday","chorshanba","среда","Hafta kunlари"], ["Thursday","payshanba","четверг","Hafta kunlari"],
  ["Friday","juma","пятница","Hafta kunlari"], ["Saturday","shanba","суббота","Hafta kunlari"], ["Sunday","yakshanba","воскресенье","Hafta kunlari"],
  ["morning","ertalab","утро","Vaqt"], ["evening","kechqurun","вечер","Vaqt"], ["night","tun","ночь","Vaqt"],
  ["today","bugun","сегодня","Vaqt"], ["tomorrow","ertaga","завтра","Vaqt"], ["yesterday","kecha","вчера","Vaqt"],
];

function genEnglishBank(mode) {
  // mode: 'uz' | 'ru' | 'en'
  const items = [];
  const seenQ = new Set();
  function randInt(a, b) { return a + Math.floor(Math.random() * (b - a + 1)); }
  function add(topic, q, correct, dists) {
    if (seenQ.has(q)) return;
    seenQ.add(q);
    let opts = [correct].concat(dists);
    opts = [...new Set(opts)];
    while (opts.length < 4) opts.push(correct + " ");
    opts = opts.slice(0, 4);
    for (let i = opts.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[opts[i], opts[j]] = [opts[j], opts[i]]; }
    items.push({ topic: topic, q: q, options: opts, correct: correct });
  }
  function sameCategoryDistractors(word, n) {
    const cat = word[3];
    const pool = EN_WORDS.filter(w => w[3] === cat && w[0] !== word[0]);
    const shuffled = pool.slice().sort(() => Math.random() - 0.5);
    const idx = mode === 'ru' ? 2 : 1;
    return shuffled.slice(0, n).map(w => w[idx]);
  }
  function sameCategoryEnDistractors(word, n) {
    const cat = word[3];
    const pool = EN_WORDS.filter(w => w[3] === cat && w[0] !== word[0]);
    const shuffled = pool.slice().sort(() => Math.random() - 0.5);
    return shuffled.slice(0, n).map(w => w[0]);
  }

  EN_WORDS.forEach(w => {
    const [en, uz, ru, cat] = w;
    const topic = mode === 'ru' ? `So'z boyligi: ${cat}` : (mode === 'en' ? `Vocabulary: ${cat}` : `So'z boyligi: ${cat}`);
    if (mode === 'uz') {
      add(topic, `'${uz}' so'zining inglizcha tarjimasi qaysi?`, en, sameCategoryEnDistractors(w, 3));
      add(topic, `'${en}' so'zining o'zbekcha ma'nosi qaysi?`, uz, sameCategoryDistractors(w, 3));
    } else if (mode === 'ru') {
      add(topic, `Как переводится слово '${ru}' на английский?`, en, sameCategoryEnDistractors(w, 3));
      add(topic, `Что означает слово '${en}' на русском?`, ru, sameCategoryDistractors(w, 3));
    } else {
      const others = EN_WORDS.filter(o => o[3] !== cat).sort(() => Math.random() - 0.5).slice(0, 3).map(o => o[0]);
      add(topic, `Which word below belongs to the category "${cat}"?`, en, others);
    }
  });

  // Grammar templates
  const Tgram = mode === 'ru' ? "Грамматика: времена глаголов" : (mode === 'en' ? "Grammar: verb tenses" : "Grammatika: fe'l zamonlari");
  const subjects = ["I", "You", "He", "She", "We", "They"];
  const verbsPresent = [["go","goes","went"],["play","plays","played"],["work","works","worked"],["study","studies","studied"],
    ["read","reads","read"],["write","writes","wrote"],["speak","speaks","spoke"],["live","lives","lived"],
    ["cook","cooks","cooked"],["clean","cleans","cleaned"],["watch","watches","watched"],["listen","listens","listened"],
    ["travel","travels","travelled"],["dance","dances","danced"],["sing","sings","sang"],["swim","swims","swam"],
    ["run","runs","ran"],["help","helps","helped"],["teach","teaches","taught"],["learn","learns","learned"]];
  subjects.forEach(subj => {
    verbsPresent.forEach(v => {
      const isThird = (subj === 'He' || subj === 'She');
      const correct = isThird ? v[1] : v[0];
      const wrong = isThird ? v[0] : v[1];
      const q = mode === 'ru'
        ? `${subj} ___ (${v[0]}) every day. Выберите правильную форму глагола.`
        : (mode === 'en' ? `${subj} ___ (${v[0]}) every day. Choose the correct verb form.` : `${subj} ___ (${v[0]}) every day. To'g'ri fe'l shaklini tanlang.`);
      add(Tgram, q, correct, [wrong, v[0] + "ing", v[2]]);

      const qPast = mode === 'ru'
        ? `${subj} ___ (${v[0]}) yesterday. Выберите правильную форму глагола (прошедшее время).`
        : (mode === 'en' ? `${subj} ___ (${v[0]}) yesterday. Choose the correct past tense form.` : `${subj} ___ (${v[0]}) yesterday. O'tgan zamon shaklini tanlang.`);
      add(Tgram, qPast, v[2], [v[0], v[1], v[0] + "ing"]);
    });
  });

  const Tprep = mode === 'ru' ? "Грамматика: предлоги" : (mode === 'en' ? "Grammar: prepositions" : "Grammatika: predloglar");
  const prepSentences = [
    ["I live __ London.", "in"], ["She is good __ maths.", "at"], ["We arrived __ the airport.", "at"],
    ["He is interested __ music.", "in"], ["The book is __ the table.", "on"], ["They go __ school every day.", "to"],
    ["I am afraid __ spiders.", "of"], ["She depends __ her parents.", "on"], ["He apologized __ the mistake.", "for"],
    ["We waited __ the bus.", "for"], ["I am proud __ you.", "of"], ["She arrived __ Tashkent.", "in"],
    ["The cat is __ the box.", "in"], ["He lives __ Navoi street.", "on"], ["I will meet you __ 5 o'clock.", "at"],
    ["She is married __ a doctor.", "to"], ["We talked __ the weather.", "about"], ["He is famous __ his songs.", "for"],
    ["I am tired __ working.", "of"], ["The keys are __ the table.", "under"], ["She sat __ me.", "next to"],
    ["He walked __ the park.", "through"], ["The shop is __ the bank.", "near"], ["We travelled __ car.", "by"],
    ["I will finish it __ Monday.", "by"], ["He was born __ 1990.", "in"], ["The meeting starts __ 9 AM.", "at"],
    ["She is angry __ him.", "with"], ["I am looking __ my keys.", "for"], ["He jumped __ the river.", "into"],
  ];
  prepSentences.forEach(([sent, correct]) => {
    const others = ["in", "on", "at", "for", "of", "to", "with", "about", "under", "near", "by", "through", "into", "next to"].filter(p => p !== correct);
    const dists = others.sort(() => Math.random() - 0.5).slice(0, 3);
    const q = mode === 'ru' ? `${sent} (выберите правильный предлог)` : (mode === 'en' ? `${sent} (choose the correct preposition)` : `${sent} (to'g'ri predlogni tanlang)`);
    add(Tprep, q, correct, dists);
  });

  return items;
}
