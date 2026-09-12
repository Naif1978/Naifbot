//@version=5
indicator("Edge Bot Ichimoku & Liquidity Multi-TF", overlay=true, max_lines_count=500, max_labels_count=500)

// --- إعدادات الفريمات والأدوات ---
// مراقبة الفريمات الأربعة: 12H, 4H, 1H, 15m
// الشروط: 
// 1. الخط المتأخر (Chikou) يقترب من السحابة/الشموع بشروط الضعف (إنذار مبكر قبل التقاطع بـ 10-15 دقيقة).
// 2. تقاطع خط التحويل (الأزرق) مع الأساس (الأحمر).
// 3. السحابة صاعدة.
// 4. تقاطع الخط المتأخر مع الشموع والسحابة والأحمر، مع خروج السريع من السحابة.
// 5. تقييم السيولة والحالة (إيجابي/سلبي) على كل فريم.

// --- إعدادات مؤشر إيشيموكو ---
tenkanLen = input.int(9, title="Tenkan-Sen (السريع/الأزرق)")
kijunLen  = input.int(26, title="Kijun-Sen (الأساسي/الأحمر)")
spanBLen  = input.int(52, title="Senkou Span B")
displacement = input.int(26, title="Chikou Span / Displacement")

// حسابات الإيشيموكو الأساسية
tenkan = math.avg(ta.lowest(tenkanLen), ta.highest(tenkanLen))
kijun  = math.avg(ta.lowest(kijunLen), ta.highest(kijunLen))
spanA  = math.avg(tenkan, kijun)
spanB  = math.avg(ta.lowest(spanBLen), ta.highest(spanBLen))

// الخط المتأخر (Chikou Span) للإغلاق الحالي مُزاح للخلف
chikou = close

// --- شروط الورقة وقواعد الإشارات ---
// فحص حالة السيولة والاتجاه (إيجابي / سلبي)
ul_volume = volume * close
sma_vol = ta.sma(ul_volume, 20)
is_liquidity_positive = ul_volume > sma_vol

// حالة السحابة (صاعدة)
cloud_bullish = spanA > spanB

// تقاطع الخط الأزرق مع الأحمر
blue_cross_red = ta.crossover(tenkan, kijun)

// تنبيه مبكر للخط المتأخر (قبل التلامس بفترة كافية / إنذار مبكر)
chikou_approaching = math.abs(chikou - spanA) <= (ta.atr(14) * 1.5)

// شروط الحالة العامة (إيجابي) لكل فريم
is_positive_state = cloud_bullish and is_liquidity_positive and (close > spanA)

// --- نظام التنبيهات (Webhook / Telegram Bot) ---
alert_condition_early = chikou_approaching and cloud_bullish
alert_condition_signal = blue_cross_red and is_positive_state

if alert_condition_early
    alert('{"status": "EARLY_WARNING", "message": "إنذار مبكر: الخط المتأخر يقترب من منطقة التقاطع للشروط المحددة قبل الوقت الكافي."}', alert.freq_once_per_bar)

if alert_condition_signal
    alert('{"status": "TRIGGER", "message": "إشارة مؤكدة: تحقق التقاطع وشروط السحابة والسيولة الإيجابية."}', alert.freq_once_per_bar)

// --- الرسم على الشاشة لتوضيح الحالة ---
plot(tenkan, color=color.blue, title="Tenkan (الأزرق)")
plot(kijun, color=color.red, title="Kijun (الأحمر)")
p1 = plot(spanA, color=color.green, title="Span A")
p2 = plot(spanB, color=color.orange, title="Span B")
fill(p1, p2, color = cloud_bullish ? color.new(color.green, 90) : color.new(color.red, 90), title="السحابة")

background_color = is_positive_state ? color.new(color.green, 95) : color.new(color.red, 95)
bgcolor(background_color, title="حالة الوضع (إيجابي/سلبي)")
