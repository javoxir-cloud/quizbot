TEST-BOT VA MINI-ILOVANI ISHGA TUSHIRISH

=== 1-QISM: ODDIY BOT (tugmali) ===

1) Python 3.13 o'rnatilgan bo'lishi kerak.
2) Shu papkada terminal oching va kerakli kutubxonalarni o'rnating:
   py -3.13 -m pip install -r requirements.txt

3) .env.example faylini nusxalab, nomini ".env" qiling, ichiga
   BotFather'dan olgan bot tokeningizni yozing:
   BOT_TOKEN=123456789:ABC...

4) Botni ishga tushiring:
   py -3.13 quizbot.py

5) Telegram'da botga /start yuboring, "📝 Test boshlash" tugmasini
   bosing, bank tanlang (Biologiya yoki Kimyo/Biokimyo).

Bot ishga tushganda avtomatik ravishda ichki veb-server ham ishga
tushadi (8080-portda) - bu Mini-ilova uchun kerak, 2-qismga qarang.


=== 2-QISM: MINI-ILOVA (chiroyli, Oson Prava kabi ko'rinish) ===

Mini-ilova ishlashi uchun botingiz internetdan ochiq (https) manzilga
ega bo'lishi kerak. Buning uchun ngrok dasturidan foydalanamiz - u
noutbukingizdagi 8080-portni vaqtincha internetga chiqarib beradi.

1) ngrok'ni yuklab oling:
   https://ngrok.com/download
   Windows uchun zip faylni oching, ichidagi ngrok.exe faylini
   shu testbot papkasiga ko'chiring (eng oson yo'l).

2) ngrok saytida bepul ro'yxatdan o'ting (https://dashboard.ngrok.com/signup),
   profilingizdan "Your Authtoken" ni toping va terminalda bir marta
   yozing:
   .\ngrok.exe config add-authtoken SIZNING_TOKENINGIZ

3) Botni ishga tushiring (agar hali ishlamayotgan bo'lsa):
   py -3.13 quizbot.py
   Buni bitta terminal oynasida OCHIQ qoldiring.

4) YANGI terminal oynasi oching (shu testbot papkasida), ngrok'ni
   ishga tushiring:
   .\ngrok.exe http 8080

   Ekranda shunga o'xshash qator chiqadi:
   Forwarding    https://abcd-12-34-56.ngrok-free.app -> http://localhost:8080

   Shu "https://....ngrok-free.app" manzilni nusxalab oling.

5) .env faylini oching (Notepad bilan), WEBAPP_URL qatoriga shu
   manzilni yozing:
   WEBAPP_URL=https://abcd-12-34-56.ngrok-free.app

   Saqlang (Ctrl+S). Botni qayta ishga tushirish shart EMAS - u
   .env faylini har safar /start bosilganda qayta o'qiydi.

6) Telegramda botga /start yuboring (yoki /mini). Endi pastda
   "🎮 Mini-ilova (chiroyli)" tugmasi chiqadi - shuni bosing, chiroyli
   veb-sahifa ko'rinishidagi test ochiladi.

MUHIM ESLATMALAR:
 - ngrok oynasini yopsangiz yoki noutbukni o'chirsangiz, Mini-ilova
   ham ishlamay qoladi (chunki u shu noutbukdan ishlayapti).
 - Bepul ngrok har safar YANGI tasodifiy manzil beradi - ngrok'ni
   qayta ishga tushirsangiz, .env dagi WEBAPP_URL ni yangi manzilga
   almashtirishni unutmang.
 - Doimiy, har doim ishlaydigan Mini-ilova kerak bo'lsa, buni bepul
   hosting xizmatiga (Render, Railway kabi) joylashtirish kerak -
   bu alohida, ko'proq sozlash talab qiladigan qadam, xohlasangiz
   keyinroq shuni ham qilib beraman.


=== SAVOL BANKLARI HAQIDA ===

 - bio.json  -> 169 ta savol (mikroskop, hujayra biologiyasi),
   DOCX fayldan olindi, savol+4 variant+to'g'ri javob aniq yozilgan
   edi (sariq rang bilan belgilangan), shuning uchun ishonchli.

 - chem.json -> 724 ta savol (biokimyo elementlari, eritmalar),
   PDF fayldan olindi. PDF'da har bir savolga faqat BITTA to'g'ri
   javob yozilgan edi (variant yo'q), shuning uchun qolgan 3 ta
   noto'g'ri variantni men shu mavzudagi boshqa savollarning
   javoblaridan tasodifiy tanlab qo'shdim. Ko'pchiligi to'g'ri
   chiqdi, lekin PDF formatlashi notekis bo'lgani uchun ayrim
   savollar matni biroz chalkash bo'lishi mumkin. Shunday savol
   uchrasa, menga ayting - shu JSON faylni tuzataman.

webapp/ papkasida index.html, bio.json va chem.json - bular
Mini-ilova uchun, botning ichki veb-serveri shu papkani xizmat
qiladi.
