<div dir="rtl">

# برنامه‌ ریز کلاسی

> راهی کوتاه برای برنامه‌ ریزی ترم تحصیلی در دانشگاه آزاد

<p>
  <img src="screenshots/dashboard.png" alt="داشبورد برنامه‌ریز کلاس‌ها" width="3839">
</p>

---

## چالش انتخاب واحد

هر ترم مجبور هستیم از بین **یک عالمه کلاس** تو سایت دانشگاه
چند تا کلاس رو طوری انتخاب کنیم که **کمترین روز** رو در دانشگاه باشیم. بعد باید نظرات دانشجویان را در مورد
اساتید توی کانال تلگرامی
چک کنیم تا به تور استاد بدقلق نیفتیم،
این پروسه هر ترم حدوداً ۲ تا ۳ ساعت تایم میبره.
بنابراین راه میان بری را ابداع کردیم.

---

## راه میان بر

**برنامه‌ریز کلاس‌ها**، اطلاعات دروس رو از پورتال [eserv.iau.ir](https://eserv.iau.ir/) استخراج می‌کنه و نظرات اساتید رو
هم از کانال
تلگرام [wtiau_asatid@](https://t.me/wtiau_asatid) در میاره، و همه ترکیب‌های ممکن رو پیدا می‌کنه.

---

## نحوه دریافت فایل‌ های دروس

۱. برو [/https://eserv.iau.ir](https://eserv.iau.ir/)    
۲. **برنامه ريزي آموزشي نيمسال تحصيلي** ← **جستجوي كلاس درسهای ارائه شده**  
۳. **تعداد نتيجه جستجو در صفحه** رو روی حداکثر بذار  
۴. با **Ctrl+S** کل صفحه رو به صورت یک فایل `html` ذخیره کن

## نحوه دریافت فایل ‌های نظرات اساتید

۱. برو کانال تلگرام [wtiau_asatid@](https://t.me/wtiau_asatid)  
۲. روی **سه نقطه (⋮)** بالا سمت راست بزن ← **Export chat history**  
۳. روی **Export** بزن و فایل رو دانلود کن  
۴. داخل پوشه دانلودی، فایل ‌های `html` رو پیدا می‌کنی

---

## نحوه استفاده

۱. **فایل ‌های `html` دروس** رو آپلود کن  
۲. **فایل ‌های `html` نظرات اساتید** رو آپلود کن  
۳. **دروس رو فیلتر کن** بر اساس نام درس و نام استاد  
۴. **تنظیمات مورد نظرت** رو اعمال کن: `روز های مجاز`، `محدوده زمانی`، `فاصله بین کلاس ‌ها`، `تعداد ترکیب ‌ها`  
۵. روی دکمه **یافتن برنامه کلاسی** بزن  
۶. نظرات اساتید رو بررسی کن

```bash
pip install -r requirements.txt

uvicorn src.main:app --reload
```

---

## تصاویر

<div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;">
  <figure style="margin:0; text-align:center; flex:1; min-width:200px;">
    <img src="screenshots/dashboard.png" alt="آپلود و فیلتر دروس">
    <figcaption>لیست دروس</figcaption>
  </figure>
  <figure style="margin:0; text-align:center; flex:1; min-width:200px;">
    <img src="screenshots/scheduler.png" alt="ترکیب‌های برنامه">
    <figcaption>ترکیب‌های کلاسی</figcaption>
  </figure>
  <figure style="margin:0; text-align:center; flex:1; min-width:200px;">
    <img src="screenshots/professors.png" alt="نظرات اساتید">
    <figcaption>نظرات</figcaption>
  </figure>
</div>

---

## تکنولوژی‌ها

ساخته شده
با [Jinja2](https://jinja.palletsprojects.com/) ،[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) ،[FastAPI](https://fastapi.tiangolo.com/)
و [OpenRouter](https://openrouter.ai/)
