(function () {
  "use strict";

  var тише = window.matchMedia &&
             window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var СЛОВАРЬ = {

    "ТП":                 { en: "TS",              zh: "变电" },
    "В":                  { en: "V",               zh: "伏" },
    "м":                  { en: "m",               zh: "米" },
    "ч":                  { en: "h",               zh: "时" },
    "кВт":                { en: "kW",              zh: "千瓦" },
    "длина линии":        { en: "line length",     zh: "线路长度" },
    "напряжение":         { en: "voltage",         zh: "电压" },
    "предел −10 %":       { en: "limit −10%",      zh: "限值 −10%" },
    "ниже предела":       { en: "below limit",     zh: "低于限值" },
    "норма":              { en: "within limit",    zh: "符合限值" },
    "запас":              { en: "margin",          zh: "裕度" },
    "нагрузка":           { en: "load",            zh: "负荷" },
    "провод заменён":     { en: "wire replaced",   zh: "已更换导线" },
    "вечерний максимум":  { en: "evening peak",    zh: "晚高峰" },
    "суточный график нагрузки":
      { en: "daily load profile", zh: "日负荷曲线" },
    "до замены":          { en: "before replacement", zh: "更换前" },
    "дальний потребитель":
      { en: "farthest consumer", zh: "末端用户" },
    "доля от установленной":
      { en: "share of installed load", zh: "占装机容量" },

    "трансформатор ТМ-250":
      { en: "transformer TM-250",  zh: "变压器 TM-250" },
    "две линии по шесть опор":
      { en: "two lines of six poles", zh: "两条线路各六基电杆" },
    "от опоры 1/3 — ответвление":
      { en: "branch from pole 1/3", zh: "从 1/3 号杆引出分支" },
    "двенадцать потребителей по 5 кВт":
      { en: "twelve consumers, 5 kW each", zh: "十二个用户，每户 5 千瓦" },
    "рассчитай пропускную способность":
      { en: "check the capacity",  zh: "校核输送能力" },
    "подстанция 250 кВ·А":
      { en: "substation 250 kVA", zh: "变电站 250 千伏安" },
    "12 опор, два фидера":
      { en: "12 poles, two feeders", zh: "12 基杆，两条馈线" },
    "ответвление: 2 опоры":
      { en: "branch: 2 poles", zh: "分支：2 基杆" },
    "12 вводов, 60 кВт":
      { en: "12 service drops, 60 kW", zh: "12 处接户线，60 千瓦" },
    "связность ОК":       { en: "connectivity OK", zh: "连通性正常" },
    "расчёт пройден":     { en: "calculation passed", zh: "计算通过" },
    "шаг":                { en: "step",            zh: "步骤" },
    "редактор":           { en: "editor",          zh: "编辑器" },
    "действие":           { en: "action",          zh: "操作" },
    "расчёт пропускной способности, F7":
      { en: "capacity calculation, F7", zh: "输送能力计算，F7" },
    "отходящая ЛЭП, две линии по шесть опор":
      { en: "outgoing lines: two lines of six poles", zh: "出线：两条线路各六基电杆" },

    "потребителей":       { en: "consumers",       zh: "用户" },
    "без ограничения":    { en: "unlimited",       zh: "无限制" },
    "Демо":               { en: "Demo",            zh: "演示版" },
    "Профессионал":       { en: "Professional",    zh: "专业版" },
    "Максимум":           { en: "Maximum",         zh: "旗舰版" },
    "эпюра и годовые потери":
      { en: "voltage profile and annual losses", zh: "电压分布图和年损耗" },
    "предел тарифа":      { en: "plan limit",      zh: "套餐上限" },
    "предел достигнут":   { en: "limit reached",   zh: "已达上限" },
    "потребителей в схеме":
      { en: "consumers in the scheme", zh: "图中用户数" },

    "редактор схемы":     { en: "scheme editor",   zh: "图纸编辑器" },
    "расчётное ядро":     { en: "calculation core", zh: "计算内核" },
    "Окно объекта":       { en: "Object window",   zh: "对象窗口" },
    "Редактор":           { en: "Editor",          zh: "编辑器" },
    "Справочник":         { en: "Catalogue",       zh: "手册" },
    "Схема замещения":    { en: "Equivalent circuit", zh: "等值电路" },
    "Расчёт":             { en: "Calculation",     zh: "计算" },
    "проверяет поля":     { en: "checks the fields", zh: "校验字段" },
    "ставит координаты":  { en: "places coordinates", zh: "布置坐标" },
    "разбирает марки":    { en: "reads wire marks", zh: "解析导线型号" },
    "узлы и ветви":       { en: "nodes and branches", zh: "节点与支路" },
    "считает и проверяет": { en: "computes and verifies", zh: "计算并校核" },
    "справочник марок":   { en: "wire catalogue",  zh: "导线手册" },
    "схема":              { en: "scheme",          zh: "图纸" },
    "опора от 1/3 и три потребителя по 5 кВт":
      { en: "pole from 1/3 and three consumers of 5 kW each",
        zh: "从 1/3 号杆引出一基杆和三个 5 千瓦用户" },
    "потребитель с cos φ = 0":
      { en: "consumer with cos φ = 0", zh: "cos φ = 0 的用户" },
    "опора 1/3, три потребителя по 5 кВт":
      { en: "pole 1/3, three consumers of 5 kW",
        zh: "1/3 号杆，三个 5 千瓦用户" },
    "cos φ = 0":          { en: "cos φ = 0",       zh: "cos φ = 0" },
    "поля верны":         { en: "fields are valid", zh: "字段有效" },
    "окно не принимает":  { en: "the window rejects it", zh: "窗口拒绝输入" },
    "марка разобрана":    { en: "wire mark read",  zh: "导线型号已解析" },
    "узлов 9, ветвей 8":  { en: "9 nodes, 8 branches", zh: "9 个节点，8 条支路" },
    "координаты расставлены":
      { en: "coordinates placed", zh: "坐标已布置" },
    "схема рассчитана":   { en: "scheme calculated", zh: "图纸已计算" },
    "схема не изменилась": { en: "the scheme is unchanged", zh: "图纸未改变" }
  };

  var язык = (function () {

    if (window.VOLTPLAN_SCENE_LANG) return window.VOLTPLAN_SCENE_LANG;
    try { return localStorage.getItem("voltplan-language") || "ru"; }
    catch (e) { return "ru"; }
  })();

  function С(строка) {
    if (язык === "ru") return строка;
    var з = СЛОВАРЬ[строка];
    return (з && з[язык]) || строка;
  }

  function чис(x, знаков) {
    var s = x.toFixed(знаков === undefined ? 0 : знаков);
    return язык === "ru" ? s.replace(".", ",") : s;
  }

  document.addEventListener("voltplan-language", function (e) {
    язык = (e && e.detail) || язык;
  });

  var П = null;
  function палитра() {
    var s = getComputedStyle(document.documentElement);
    function v(имя, зап) {
      var z = s.getPropertyValue(имя);
      return (z && z.trim()) || зап;
    }
    var тьма = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      тьма:     тьма,
      чернила:  v("--ink", "#0a1220"),
      чернила2: v("--ink-2", "#1b2740"),
      тихий:    v("--muted", "#56668a"),
      акцент:   v("--accent", "#1348e0"),
      акцентТ:  v("--accent-d", "#0d34ad"),
      акцентС:  v("--accent-l", "#4c7bff"),
      линия:    v("--line", "#e2e7f1"),
      линия2:   v("--line-2", "#ccd5e6"),
      поле:     v("--surface", "#ffffff"),
      бумага:   v("--paper-2", "#f6f8fc"),
      добро:    v("--ok", "#0f8a4d"),

      беда:     тьма ? "#f2777a" : "#c0392b",
      бетон:    тьма ? "#8b98b4" : "#9aa6be",

      мягкийА:  тьма ? "rgba(76,123,255,.16)" : "rgba(19,72,224,.09)",
      мягкийД:  тьма ? "rgba(52,211,153,.16)" : "rgba(15,138,77,.10)",
      мягкийБ:  тьма ? "rgba(242,119,122,.16)" : "rgba(192,57,43,.08)",
      стекло:   тьма ? "rgba(15,24,41,.86)" : "rgba(255,255,255,.90)"
    };
  }
  П = палитра();
  new MutationObserver(function () { П = палитра(); })
    .observe(document.documentElement, { attributes: true,
                                         attributeFilter: ["data-theme"] });

  var ШРИФТ = '"Inter","Segoe UI",system-ui,sans-serif';
  var МОНО = '"JetBrains Mono","Cascadia Code",ui-monospace,Consolas,monospace';

  function холст(id) {
    var c = document.getElementById(id);
    if (!c || !c.getContext) return null;
    var ctx = c.getContext("2d");
    var Ш = 0, В = 0;
    function размер() {
      var п = Math.min(window.devicePixelRatio || 1, 2);
      var r = c.getBoundingClientRect();
      Ш = Math.max(300, Math.round(r.width));
      В = Math.max(180, Math.round(r.height));
      c.width = Math.round(Ш * п);
      c.height = Math.round(В * п);
      ctx.setTransform(п, 0, 0, п, 0, 0);
    }
    размер();
    window.addEventListener("resize", размер);
    return { узел: c, ctx: ctx, размер: размер,
             ш: function () { return Ш; }, в: function () { return В; } };
  }

  var СДВИГ = null;

  var прежний = window.voltplanSceneSeek;
  window.voltplanSceneSeek = function (с) {
    СДВИГ = (с === null || с === undefined) ? null : +с;
    if (typeof прежний === "function") прежний(с);
  };

  function крутить(к, кадр) {
    var видна = true, t0 = 0, стоп = false;
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (з) {
        видна = з[0].isIntersecting;
      }, { threshold: 0.02 }).observe(к.узел);
    }
    function шаг(t) {
      if (стоп) return;
      if (!t0) t0 = t;
      if (видна) кадр(СДВИГ === null ? (t - t0) / 1000 : СДВИГ);
      requestAnimationFrame(шаг);
    }

    кадр(0);

    if (тише) {
      var перерисовать = function () { к.размер(); кадр(-1); };
      перерисовать();
      window.addEventListener("resize", перерисовать);
      document.addEventListener("voltplan-language", перерисовать);
      new MutationObserver(перерисовать).observe(
        document.documentElement,
        { attributes: true, attributeFilter: ["data-theme"] });
      return;
    }
    requestAnimationFrame(шаг);
  }

  function путьСкругл(ctx, x, y, ш, в, r) {
    r = Math.min(r, ш / 2, в / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + ш, y, x + ш, y + в, r);
    ctx.arcTo(x + ш, y + в, x, y + в, r);
    ctx.arcTo(x, y + в, x, y, r);
    ctx.arcTo(x, y, x + ш, y, r);
    ctx.closePath();
  }

  function плашка(ctx, x, y, текст, цвет, фон, справа, кегль) {
    ctx.font = "600 " + (кегль || 12) + "px " + ШРИФТ;
    var ш = ctx.measureText(текст).width + 18;
    var в = (кегль || 12) + 10;
    if (справа) x -= ш;
    путьСкругл(ctx, x, y, ш, в, в / 2);
    ctx.fillStyle = фон;
    ctx.fill();
    ctx.fillStyle = цвет;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(текст, x + 9, y + в / 2 + 0.5);
    return ш;
  }

  function домик(ctx, x, y, ш, цвет) {
    var в = ш * 0.74, к = ш * 0.42;
    ctx.fillStyle = цвет;
    ctx.beginPath();
    ctx.rect(x - ш / 2, y - в, ш, в);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x - ш / 2 - 1.5, y - в);
    ctx.lineTo(x, y - в - к);
    ctx.lineTo(x + ш / 2 + 1.5, y - в);
    ctx.closePath();
    ctx.fill();
  }

  function плавно(t) {
    t = Math.max(0, Math.min(1, t));
    return t * t * (3 - 2 * t);
  }

  function гладкая(ctx, т) {
    if (т.length < 2) return;
    ctx.moveTo(т[0].x, т[0].y);
    for (var i = 0; i < т.length - 1; i++) {
      var p0 = т[i - 1] || т[i], p1 = т[i], p2 = т[i + 1], p3 = т[i + 2] || p2;
      ctx.bezierCurveTo(p1.x + (p2.x - p0.x) / 6, p1.y + (p2.y - p0.y) / 6,
                        p2.x - (p3.x - p1.x) / 6, p2.y - (p3.y - p1.y) / 6,
                        p2.x, p2.y);
    }
  }

  function карточка(ctx, x, y, ш, в, r, фон, кром) {
    путьСкругл(ctx, x, y, ш, в, r === undefined ? 12 : r);
    ctx.fillStyle = фон || П.поле;
    ctx.fill();
    if (кром !== false) {
      ctx.strokeStyle = кром || П.линия;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  function влезает(ctx, текст, предел) {
    if (ctx.measureText(текст).width <= предел) return текст;
    var т = текст;
    while (т.length > 1 && ctx.measureText(т + "…").width > предел) {
      т = т.slice(0, -1);
    }
    return т + "…";
  }

  function эпюра() {
    var к = холст("anim-voltage");
    if (!к) return;
    var ctx = к.ctx;

    var ПРОЛЁТ = 55;
    var N = 12;
    var UНОМ = 220;
    var ПРЕДЕЛ = 198;
    var COS = 0.92, SIN = 0.392;

    var МАРКА = [{ имя: "СИП-4 4×35", r: 0.868, x: 0.088, толщ: 2.0 },
                 { имя: "СИП-4 4×70", r: 0.443, x: 0.082, толщ: 3.4 }];
    var ДОМА = [{ оп: 2, P: 8 }, { оп: 4, P: 6 }, { оп: 6, P: 10 },
                { оп: 8, P: 7 }, { оп: 10, P: 9 }, { оп: 12, P: 12 }];

    var СУТКИ = [[0, .22], [4, .18], [6, .35], [8, .72], [10, .55],
                 [12, .50], [14, .45], [17, .62], [20, 1.0], [22, .75],
                 [24, .22]];

    function доля(ч) {
      for (var i = 1; i < СУТКИ.length; i++) {
        if (ч <= СУТКИ[i][0]) {
          var a = СУТКИ[i - 1], b = СУТКИ[i];
          var t = плавно((ч - a[0]) / (b[0] - a[0]));
          return a[1] + (b[1] - a[1]) * t;
        }
      }
      return СУТКИ[СУТКИ.length - 1][1];
    }

    function профиль(ч, м) {
      var r = МАРКА[0].r + (МАРКА[1].r - МАРКА[0].r) * м;
      var x = МАРКА[0].x + (МАРКА[1].x - МАРКА[0].x) * м;
      var z = r * COS + x * SIN;
      var k = доля(ч), U = [UНОМ], пад = 0, нагр = 0, j, i;
      for (j = 1; j <= N; j++) {
        var P = 0;
        for (i = 0; i < ДОМА.length; i++) {
          if (ДОМА[i].оп >= j) P += ДОМА[i].P * k;
        }
        var I = P * 1000 / (3 * UНОМ * COS);
        var dU = Math.sqrt(3) * I * z * (ПРОЛЁТ / 1000);
        пад += dU / Math.sqrt(3);
        U.push(UНОМ - пад);
      }
      for (i = 0; i < ДОМА.length; i++) нагр += ДОМА[i].P * k;
      return { U: U, нагрузка: нагр };
    }

    var ЦИКЛ = 25.0;
    function состояние(t) {
      if (t < 0) return { ч: 20, м: 0, тревога: 1, замена: 0, финал: 0 };
      var с = t % ЦИКЛ;
      if (с < 12) return { ч: с / 12 * 20, м: 0, тревога: 0,
                           замена: 0, финал: 0 };
      if (с < 15.5) return { ч: 20, м: 0, тревога: плавно((с - 12) / 1.2),
                             замена: 0, финал: 0 };
      if (с < 19) return { ч: 20, м: плавно((с - 15.5) / 3.0),
                           тревога: 1 - плавно((с - 15.5) / 3.0),
                           замена: плавно((с - 15.5) / 1.0), финал: 0 };
      if (с < 22.5) return { ч: 20, м: 1, тревога: 0, замена: 1,
                             финал: плавно((с - 19) / 1.2) };
      var у = плавно((с - 22.5) / 2.5);
      return { ч: 20, м: 1 - у, тревога: 0, замена: 1 - у, финал: 1 - у };
    }

    function часы(ч) {
      var чч = Math.floor(ч) % 24, мм = Math.floor((ч - Math.floor(ч)) * 6) * 10;
      return (чч < 10 ? "0" : "") + чч + ":" + (мм < 10 ? "0" : "") + мм;
    }

    крутить(к, function (t) {
      var Ш = к.ш(), В = к.в(), с = состояние(t);
      var пр = профиль(с.ч, с.м);
      var исходный = профиль(с.ч, 0);
      var Uк = пр.U[N], i, у;
      ctx.clearRect(0, 0, Ш, В);

      var компакт = В < 350;
      var Л = 52, Пр = 16;
      var yСтрока = 9, вСтрока = 24;
      var вВид = компакт ? 58 : 74;
      var вЛента = компакт ? 48 : 62;
      var провод = yСтрока + вСтрока + (компакт ? 12 : 16);
      var земля = провод + (компакт ? 30 : 40);
      var Верх = земля + (компакт ? 16 : 22);
      var Низ = В - вЛента - (компакт ? 30 : 38);
      var шГ = Ш - Л - Пр, вГ = Низ - Верх;
      var Uверх = 233, Uниз = 196;
      function X(д) { return Л + шГ * д; }
      function Y(u) { return Низ - (u - Uниз) / (Uверх - Uниз) * вГ; }

      var первыйПлохой = -1;
      for (i = 1; i <= N; i++) {
        if (пр.U[i] < ПРЕДЕЛ) { первыйПлохой = i; break; }
      }
      var хорошо = Uк >= ПРЕДЕЛ;

      ctx.textBaseline = "middle";
      var чт = часы(с.ч) + "  ·  " + чис(пр.нагрузка, 1) + " " + С("кВт");
      var шп = плашка(ctx, Л, yСтрока, чт, П.поле,
                      П.тьма ? "rgba(76,123,255,.92)" : "rgba(19,72,224,.94)");
      if (с.ч > 18.6) {
        ctx.font = "600 11px " + ШРИФТ;
        ctx.fillStyle = П.тихий;
        ctx.textAlign = "left";
        ctx.fillText(С("вечерний максимум"), Л + шп + 12, yСтрока + 11);
      }
      var состТекст, состЦвет;
      if (с.замена > 0.02 && с.финал < 0.5) {
        состТекст = С("провод заменён") + " · " + МАРКА[1].имя;
        состЦвет = П.добро;
      } else if (!хорошо) {
        состТекст = С("ниже предела") + " · Umin " + чис(Uк, 1) + " " + С("В");
        состЦвет = П.беда;
      } else {
        состТекст = С("норма") + " · " + С("запас") + " " +
                    чис(Uк - ПРЕДЕЛ, 1) + " " + С("В");
        состЦвет = П.добро;
      }
      плашка(ctx, Ш - Пр, yСтрока, состТекст, П.поле, состЦвет, true);

      ctx.strokeStyle = П.линия;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(Л - 34, земля + .5);
      ctx.lineTo(Ш - Пр, земля + .5);
      ctx.stroke();

      var толщ = МАРКА[0].толщ + (МАРКА[1].толщ - МАРКА[0].толщ) * с.м;
      ctx.lineCap = "round";
      for (i = 1; i <= N; i++) {
        var xо = X(i / N);
        var плохо = первыйПлохой > 0 && i >= первыйПлохой;
        ctx.strokeStyle = плохо ? П.беда : П.акцент;
        ctx.globalAlpha = плохо ? 0.6 + 0.4 * с.тревога : 0.85;
        ctx.lineWidth = толщ;
        ctx.beginPath();
        ctx.moveTo(i === 1 ? Л - 12 : X((i - 1) / N), провод);
        ctx.lineTo(xо, провод);
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = П.бетон;
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(xо, провод - 2);
        ctx.lineTo(xо, земля);
        ctx.stroke();
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(xо - 5, провод + 3);
        ctx.lineTo(xо + 5, провод + 3);
        ctx.stroke();
      }

      ctx.font = "600 10.5px " + МОНО;
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillStyle = с.замена > 0.02 ? П.добро : П.тихий;
      ctx.fillText(с.м > 0.5 ? МАРКА[1].имя : МАРКА[0].имя, Л, провод - 8);

      for (i = 0; i < ДОМА.length; i++) {
        var xд = X(ДОМА[i].оп / N);
        var сдв = (xд + 20 > Ш - Пр) ? -12 : 12;
        var бедный = первыйПлохой > 0 && ДОМА[i].оп >= первыйПлохой;
        ctx.strokeStyle = бедный ? П.беда : П.акцентС;
        ctx.globalAlpha = .75;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(xд, провод);
        ctx.lineTo(xд + сдв, земля - 11);
        ctx.stroke();
        ctx.globalAlpha = 1;
        домик(ctx, xд + сдв, земля, 13,
              бедный ? П.беда : (П.тьма ? "#6c7ea6" : "#c3cde2"));
      }

      ctx.fillStyle = П.тьма ? "#22304d" : "#dbe3f2";
      путьСкругл(ctx, Л - 40, земля - 34, 30, 34, 5);
      ctx.fill();
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 1.4;
      ctx.stroke();
      ctx.fillStyle = П.акцент;
      ctx.font = "700 10.5px " + ШРИФТ;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(С("ТП"), Л - 25, земля - 17);

      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.font = "500 11px " + МОНО;
      for (у = 200; у <= 230; у += 10) {
        var yy = Math.round(Y(у)) + .5;
        ctx.strokeStyle = П.линия;
        ctx.beginPath();
        ctx.moveTo(Л, yy);
        ctx.lineTo(Ш - Пр, yy);
        ctx.stroke();
        ctx.fillStyle = П.тихий;
        ctx.fillText(чис(у), Л - 9, yy);
      }
      ctx.fillStyle = П.тихий;
      ctx.font = "500 10.5px " + ШРИФТ;
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillText(С("напряжение") + ", " + С("В"), Л, Верх - 4);

      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.font = "500 11px " + МОНО;
      for (i = 0; i <= 4; i++) {
        var xм = X(i / 4);
        ctx.strokeStyle = П.линия;
        ctx.beginPath();
        ctx.moveTo(xм + .5, Низ);
        ctx.lineTo(xм + .5, Низ + 4);
        ctx.stroke();
        ctx.fillStyle = П.тихий;
        ctx.fillText(чис(i / 4 * N * ПРОЛЁТ), xм, Низ + 7);
      }

      ctx.font = "500 10.5px " + ШРИФТ;
      ctx.textAlign = "right";
      ctx.fillText(С("длина линии") + ", " + С("м"), Ш - Пр, Низ + 20);

      ctx.setLineDash([2, 4]);
      ctx.strokeStyle = П.линия;
      for (i = 0; i < ДОМА.length; i++) {
        var xн = X(ДОМА[i].оп / N);
        ctx.beginPath();
        ctx.moveTo(xн + .5, земля + 2);
        ctx.lineTo(xн + .5, Y(пр.U[ДОМА[i].оп]));
        ctx.stroke();
      }
      ctx.setLineDash([]);

      function узлы(U) {
        var т = [];
        for (var j = 0; j <= N; j++) т.push({ x: X(j / N), y: Y(U[j]) });
        return т;
      }
      var текущие = узлы(пр.U);

      var зал = ctx.createLinearGradient(0, Верх, 0, Низ);
      зал.addColorStop(0, П.тьма ? "rgba(76,123,255,.26)" : "rgba(19,72,224,.17)");
      зал.addColorStop(1, "rgba(19,72,224,0)");
      ctx.beginPath();
      гладкая(ctx, текущие);
      ctx.lineTo(X(1), Низ);
      ctx.lineTo(X(0), Низ);
      ctx.closePath();
      ctx.fillStyle = зал;
      ctx.fill();

      var yП = Y(ПРЕДЕЛ);

      ctx.fillStyle = П.мягкийБ;
      ctx.fillRect(Л, yП, шГ, Низ - yП);

      if (хорошо) {
        ctx.save();
        ctx.beginPath();
        гладкая(ctx, текущие);
        ctx.lineTo(X(1), yП);
        ctx.lineTo(X(0), yП);
        ctx.closePath();

        var зап = ctx.createLinearGradient(0, yП, 0, yП - (yП - Верх) * 0.5);
        зап.addColorStop(0, П.тьма ? "rgba(52,211,153,.34)"
                                   : "rgba(15,138,77,.22)");
        зап.addColorStop(1, "rgba(15,138,77,0)");
        ctx.fillStyle = зап;
        ctx.fill();
        ctx.restore();
      }

      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = П.беда;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.moveTo(Л, yП + .5);
      ctx.lineTo(Ш - Пр, yП + .5);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "600 10.5px " + ШРИФТ;
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      ctx.fillStyle = П.беда;
      ctx.fillText(С("предел −10 %") + " · " + чис(ПРЕДЕЛ) + " " + С("В"),
                   Л + 6, yП - 4);

      if (с.м > 0.03) {
        ctx.save();
        ctx.globalAlpha = 0.55 * Math.min(1, с.м * 2);
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = П.бетон;
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        гладкая(ctx, узлы(исходный.U));
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
        ctx.restore();
        if (с.м > 0.55) {
          ctx.font = "500 10px " + ШРИФТ;
          ctx.fillStyle = П.бетон;
          ctx.textAlign = "right";
          ctx.textBaseline = "top";
          ctx.fillText(С("до замены"), X(1) - 4, Y(исходный.U[N]) + 5);
        }
      }

      function кривая() {
        ctx.beginPath();
        гладкая(ctx, текущие);
        ctx.stroke();
      }
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 2.6;
      ctx.lineJoin = "round";
      кривая();
      ctx.save();
      ctx.beginPath();
      ctx.rect(Л, yП, шГ, Низ - yП);
      ctx.clip();
      ctx.strokeStyle = П.беда;
      ctx.lineWidth = 3.0;
      кривая();
      ctx.restore();

      for (i = 0; i < ДОМА.length; i++) {
        var о = ДОМА[i].оп, xт = X(о / N), yт = Y(пр.U[о]);
        ctx.beginPath();
        ctx.arc(xт, yт, 3.4, 0, Math.PI * 2);
        ctx.fillStyle = пр.U[о] < ПРЕДЕЛ ? П.беда : П.акцент;
        ctx.fill();
        ctx.strokeStyle = П.поле;
        ctx.lineWidth = 1.6;
        ctx.stroke();
      }

      var xк = X(1), yк = Y(Uк);
      var yпод = Math.max(Верх + 14, Math.min(Низ - 30, yк - 34));
      ctx.strokeStyle = хорошо ? П.добро : П.беда;
      ctx.globalAlpha = .55;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(xк, yк - 5);
      ctx.lineTo(xк, yпод + 22);
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.textBaseline = "middle";
      плашка(ctx, Ш - Пр, yпод,
             чис(Uк, 1) + " " + С("В"), П.поле,
             хорошо ? П.добро : П.беда, true);
      ctx.font = "500 9.5px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "right";
      ctx.textBaseline = "bottom";
      ctx.fillText(С("дальний потребитель"), Ш - Пр, yпод - 3);

      var yЛ = В - вЛента + 2, вЛ = вЛента - 14;
      var Лл = Л, шЛ = Ш - Л - Пр;
      карточка(ctx, Лл, yЛ, шЛ, вЛ, 8, П.бумага, П.линия);
      function Xч(ч) { return Лл + шЛ * (ч / 24); }
      function Yд(d) { return yЛ + вЛ - 4 - d * (вЛ - 12); }

      var сут = [];
      for (i = 0; i <= 48; i++) сут.push({ x: Xч(i / 2), y: Yд(доля(i / 2)) });
      ctx.beginPath();
      гладкая(ctx, сут);
      ctx.lineTo(Xч(24), yЛ + вЛ);
      ctx.lineTo(Xч(0), yЛ + вЛ);
      ctx.closePath();
      ctx.fillStyle = П.мягкийА;
      ctx.fill();
      ctx.beginPath();
      гладкая(ctx, сут);
      ctx.strokeStyle = П.акцентС;
      ctx.lineWidth = 1.6;
      ctx.stroke();

      ctx.font = "500 9px " + МОНО;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      for (i = 0; i <= 24; i += 6) {
        ctx.strokeStyle = П.линия;
        ctx.beginPath();
        ctx.moveTo(Xч(i) + .5, yЛ + вЛ - 4);
        ctx.lineTo(Xч(i) + .5, yЛ + вЛ);
        ctx.stroke();
        if (i < 24) ctx.fillText(i + ":00", Xч(i) + (i === 0 ? 14 : 0), yЛ + вЛ + 2);
      }
      ctx.textAlign = "left";
      ctx.font = "600 9.5px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.textBaseline = "top";
      ctx.fillText(С("суточный график нагрузки"), Лл + 8, yЛ + 3);

      var xт2 = Xч(с.ч);
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(xт2, yЛ + 2);
      ctx.lineTo(xт2, yЛ + вЛ - 2);
      ctx.stroke();
      var yт2 = Yд(доля(с.ч));
      ctx.beginPath();
      ctx.arc(xт2, yт2, 3.6, 0, Math.PI * 2);
      ctx.fillStyle = П.акцент;
      ctx.fill();
      ctx.strokeStyle = П.поле;
      ctx.lineWidth = 1.6;
      ctx.stroke();

      if (с.ч > 18.6) {
        ctx.beginPath();
        ctx.arc(xт2, yт2, 7 + 2 * Math.sin((t < 0 ? 0 : t) * 4), 0, Math.PI * 2);
        ctx.strokeStyle = П.беда;
        ctx.globalAlpha = .5;
        ctx.lineWidth = 1.4;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    });
  }

  function стройка() {
    var к = холст("anim-build");
    if (!к) return;
    var ctx = к.ctx;

    var ШАГИ = [
      { фраза: "трансформатор ТМ-250",           ответ: "подстанция 250 кВ·А" },
      { фраза: "отходящая ЛЭП, две линии по шесть опор", ответ: "12 опор, два фидера" },
      { фраза: "от опоры 1/3 — ответвление",     ответ: "ответвление: 2 опоры" },
      { фраза: "двенадцать потребителей по 5 кВт", ответ: "12 вводов, 60 кВт" },
      { фраза: "расчёт пропускной способности, F7", ответ: null }
    ];
    var ШАГ = 4.6;
    var ЦИКЛ = ШАГ * ШАГИ.length + 4.0;

    крутить(к, function (t) {
      var Ш = к.ш(), В = к.в();
      var с = t < 0 ? ШАГ * 4.6 : (t % ЦИКЛ);
      var шагN = Math.min(ШАГИ.length - 1, Math.floor(с / ШАГ));
      var внутри = (с - шагN * ШАГ) / ШАГ;
      var уход = с > ШАГ * ШАГИ.length + 2.6
        ? плавно((с - ШАГ * ШАГИ.length - 2.6) / 1.4) : 0;
      ctx.clearRect(0, 0, Ш, В);
      ctx.globalAlpha = 1 - уход;

      var поля = 14;
      var шЛенты = Math.max(210, Math.min(360, Ш * 0.30));
      var узко = Ш < 620;
      if (узко) шЛенты = Math.max(150, Ш * 0.34);
      var xЛист = поля + шЛенты + 14;
      var шЛист = Ш - xЛист - поля;

      function готов(k) {
        if (шагN > k) return 1;
        if (шагN < k) return 0;
        return плавно(Math.max(0, (внутри - 0.26) / 0.48));
      }

      лента(ctx, поля, поля, шЛенты, В - поля * 2, шагN, внутри, ШАГИ, t);
      лист(ctx, xЛист, поля, шЛист, В - поля * 2, готов, шагN, внутри, t);
      ctx.globalAlpha = 1;
    });

    function лента(ctx, x, y, ш, в, шагN, внутри, ШАГИ, t) {
      карточка(ctx, x, y, ш, в, 12, П.бумага, П.линия);
      var вн = 12, xс = x + вн, шс = ш - вн * 2;

      ctx.font = "700 10px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(С("действие").toUpperCase() + " · " + С("редактор").toUpperCase(),
                   xс, y + 9);

      var строки = [];
      for (var i = 0; i <= шагN; i++) {
        var видно = i < шагN ? ШАГИ[i].фраза.length
          : Math.ceil(С(ШАГИ[i].фраза).length * Math.min(1, внутри / 0.24));
        строки.push({ чей: "я", текст: С(ШАГИ[i].фраза), видно: видно,
                      печатает: i === шагN && внутри < 0.24 });
        var готовОтвет = i < шагN || внутри > 0.55;
        if (ШАГИ[i].ответ && готовОтвет) {
          строки.push({ чей: "он", текст: С(ШАГИ[i].ответ), видно: 999 });
        }
      }

      ctx.font = "600 12px " + ШРИФТ;
      var зазор = 7, yТек = y + в - вн;
      var кучка = [];
      for (var j = строки.length - 1; j >= 0; j--) {
        var р = строки[j];
        var т = р.текст.slice(0, р.видно);
        var шТ = Math.min(шс - 22, шс * 0.94);
        var линии = перенос(ctx, т, шТ - 20);
        var вБ = линии.length * 16 + 14;
        yТек -= вБ;
        if (yТек < y + 26) break;
        кучка.push({ р: р, y: yТек, линии: линии, ш: шТ });
        yТек -= зазор;
      }
      кучка.forEach(function (э) {
        var р = э.р, мой = р.чей === "я";
        var вБ = э.линии.length * 16 + 14;
        var шБ = 0;
        ctx.font = "600 12px " + ШРИФТ;
        э.линии.forEach(function (л) {
          шБ = Math.max(шБ, ctx.measureText(л).width);
        });
        шБ = Math.min(э.ш, шБ + 20);
        var xБ = мой ? xс : xс + (шс - шБ);
        путьСкругл(ctx, xБ, э.y, шБ, вБ, 9);
        ctx.fillStyle = мой
          ? (П.тьма ? "rgba(76,123,255,.18)" : "rgba(19,72,224,.09)")
          : П.поле;
        ctx.fill();
        ctx.strokeStyle = мой
          ? (П.тьма ? "rgba(76,123,255,.32)" : "rgba(19,72,224,.18)")
          : П.линия;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = мой ? П.чернила : П.добро;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.font = мой ? "600 12px " + ШРИФТ : "600 11.5px " + ШРИФТ;
        э.линии.forEach(function (л, i2) {
          ctx.fillText(л, xБ + 10, э.y + 15 + i2 * 16);
        });
        if (р.печатает && Math.floor(t * 2) % 2 === 0) {
          var последняя = э.линии[э.линии.length - 1] || "";
          ctx.font = "600 12px " + ШРИФТ;
          var шТ2 = ctx.measureText(последняя).width;
          ctx.fillStyle = П.акцент;
          ctx.fillRect(xБ + 11 + шТ2, э.y + вБ - 22, 1.6, 13);
        }
      });
    }

    function перенос(ctx, текст, предел) {
      var слова = текст.split(" "), строки = [], тек = "";
      for (var i = 0; i < слова.length; i++) {
        var проба = тек ? тек + " " + слова[i] : слова[i];
        if (ctx.measureText(проба).width > предел && тек) {
          строки.push(тек);
          тек = слова[i];
        } else {
          тек = проба;
        }
      }
      if (тек || !строки.length) строки.push(тек);
      return строки;
    }

    function лист(ctx, x, y, ш, в, готов, шагN, внутри, t) {
      карточка(ctx, x, y, ш, в, 12, П.поле, П.линия);
      ctx.save();
      путьСкругл(ctx, x, y, ш, в, 12);
      ctx.clip();

      ctx.fillStyle = П.линия;
      ctx.globalAlpha = (П.тьма ? .55 : .95) * ctx.globalAlpha;
      for (var gx = x + 18; gx < x + ш; gx += 22) {
        for (var gy = y + 30; gy < y + в; gy += 22) ctx.fillRect(gx, gy, 1.3, 1.3);
      }
      ctx.globalAlpha = 1;

      var шШ = 22, xШ = x + ш - 14 - шШ * 5 - 4 * 4;
      for (var i = 0; i < 5; i++) {
        var xс = xШ + i * (шШ + 4);
        ctx.fillStyle = i < шагN ? П.акцент
          : (i === шагN ? П.акцентС : П.линия2);
        ctx.globalAlpha = i === шагN ? 0.45 + 0.55 * внутри : 1;
        путьСкругл(ctx, xс, y + 12, шШ, 3.5, 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      ctx.font = "600 9.5px " + МОНО;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(С("шаг") + " " + (шагN + 1) + "/5", x + 14, y + 14);

      var л = x + ш * 0.14, п = x + ш * 0.93;
      var шагX = (п - л) / 5;
      var верх = y + в * 0.44, низ = y + в * 0.80, ветка = y + в * 0.20;
      var тп = { x: x + ш * 0.055, y: y + в * 0.62 };
      var A = [], B = [], C = [], j;
      for (j = 0; j < 6; j++) {
        A.push({ x: л + шагX * j, y: верх });
        B.push({ x: л + шагX * j, y: низ });
      }
      for (j = 0; j < 2; j++) C.push({ x: A[2].x + шагX * (j + 0.5), y: ветка });
      var дома = [
        { о: A[1], с: -1 }, { о: A[2], с: -1 }, { о: A[3], с: -1 },
        { о: A[4], с: -1 }, { о: A[5], с: -1 },
        { о: B[1], с: 1 }, { о: B[2], с: 1 }, { о: B[3], с: 1 },
        { о: B[4], с: 1 }, { о: B[5], с: 1 },
        { о: C[0], с: 1 }, { о: C[1], с: 1 }
      ];

      var перо = null;

      function растёт(a, b, p) {
        if (p <= 0) return;
        var к = { x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p };
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(к.x, к.y);
        ctx.stroke();
        if (p < 1) перо = к;
      }

      function опора(т, p) {
        if (p <= 0) return;
        var r = 4.4 * Math.min(1, p * 1.6);
        ctx.strokeStyle = П.бетон;
        ctx.lineWidth = 1.7;
        ctx.beginPath();
        ctx.moveTo(т.x, т.y - 6.5 * Math.min(1, p * 1.6));
        ctx.lineTo(т.x, т.y + 6.5 * Math.min(1, p * 1.6));
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(т.x, т.y, r, 0, Math.PI * 2);
        ctx.fillStyle = П.поле;
        ctx.fill();
        ctx.strokeStyle = П.акцент;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      var g2 = готов(1);
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 2.1;
      ctx.lineCap = "round";
      if (g2 > 0) {
        for (j = 0; j < 6; j++) {
          var p = Math.max(0, Math.min(1, g2 * 6 - j));
          растёт(j === 0 ? тп : A[j - 1], A[j], p);
          растёт(j === 0 ? тп : B[j - 1], B[j], p);
          опора(A[j], p);
          опора(B[j], p);
        }
      }

      var g3 = готов(2);
      if (g3 > 0) {
        ctx.strokeStyle = П.акцент;
        ctx.lineWidth = 2.1;
        for (j = 0; j < C.length; j++) {
          var p3 = Math.max(0, Math.min(1, g3 * 2 - j));
          растёт(j === 0 ? A[2] : C[j - 1], C[j], p3);
          опора(C[j], p3);
        }
      }

      var g4 = готов(3);
      if (g4 > 0) {
        for (j = 0; j < дома.length; j++) {
          var д = дома[j];
          var p4 = Math.max(0, Math.min(1, g4 * дома.length - j));
          if (p4 <= 0) continue;
          var yд = д.о.y + д.с * 27 * p4;
          ctx.strokeStyle = П.акцентС;
          ctx.lineWidth = 1.3;
          ctx.beginPath();
          ctx.moveTo(д.о.x, д.о.y);
          ctx.lineTo(д.о.x, yд);
          ctx.stroke();
          домик(ctx, д.о.x, yд + (д.с > 0 ? 12 : 0),
                13 * Math.min(1, p4 * 1.4),
                П.тьма ? "#7286ae" : "#b9c5dd");
        }
      }

      var g1 = готов(0);
      if (g1 > 0) {
        ctx.globalAlpha = Math.min(1, g1 * 2) * ctx.globalAlpha;
        var шТП = 42, вТП = 36;
        путьСкругл(ctx, тп.x - шТП / 2, тп.y - вТП / 2, шТП, вТП, 7);
        ctx.fillStyle = П.тьма ? "#22304d" : "#dde5f4";
        ctx.fill();
        ctx.strokeStyle = П.акцент;
        ctx.lineWidth = 1.7;
        ctx.stroke();
        ctx.fillStyle = П.акцент;
        ctx.font = "700 12px " + ШРИФТ;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(С("ТП"), тп.x, тп.y);
        ctx.globalAlpha = 1;
      }

      var g5 = готов(4);
      if (g5 > 0) {
        var xВ = x + ш * 0.02 + ш * 0.99 * g5;
        var гр = ctx.createLinearGradient(xВ - 70, 0, xВ, 0);
        гр.addColorStop(0, "rgba(15,138,77,0)");
        гр.addColorStop(1, П.тьма ? "rgba(52,211,153,.26)" : "rgba(15,138,77,.17)");
        ctx.fillStyle = гр;
        ctx.fillRect(xВ - 70, y, 70, в);
        ctx.strokeStyle = П.добро;
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.85 * ctx.globalAlpha;
        ctx.beginPath();
        ctx.moveTo(xВ, y);
        ctx.lineTo(xВ, y + в);
        ctx.stroke();
        ctx.globalAlpha = 1;
        var узлы2 = A.concat(B, C);
        for (j = 0; j < узлы2.length; j++) {
          if (узлы2[j].x > xВ) continue;
          ctx.beginPath();
          ctx.arc(узлы2[j].x, узлы2[j].y, 4.4, 0, Math.PI * 2);
          ctx.fillStyle = П.добро;
          ctx.fill();
          ctx.strokeStyle = П.поле;
          ctx.lineWidth = 1.7;
          ctx.stroke();
        }
      }

      if (перо) {
        ctx.beginPath();
        ctx.arc(перо.x, перо.y, 3.2, 0, Math.PI * 2);
        ctx.fillStyle = П.акцент;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(перо.x, перо.y, 8 + 2 * Math.sin((t < 0 ? 0 : t) * 9), 0,
                Math.PI * 2);
        ctx.strokeStyle = П.акцент;
        ctx.globalAlpha = 0.35 * ctx.globalAlpha;
        ctx.lineWidth = 1.4;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      ctx.restore();

      if (g5 > 0.97) {
        ctx.textBaseline = "middle";
        var текст = "Umin " + чис(219.4, 1) + " " + С("В") + "  ·  " +
                    С("связность ОК") + "  ·  " + С("расчёт пройден");
        плашка(ctx, x + ш - 14, y + в - 34, текст, П.поле, П.добро, true);
      }
    }
  }

  function тарифы() {
    var к = холст("anim-tiers");
    if (!к) return;
    var ctx = к.ctx;

    var ВСЕГО = 598;
    var МАЛО = 40;
    var РУБЕЖ = [{ n: МАЛО, имя: "Демо" },
                 { n: ВСЕГО, имя: "Профессионал" },
                 { n: ВСЕГО, имя: "Максимум" }];

    var ТОЧКИ = [], РОДИТЕЛЬ = [], ВЕС = [];
    (function () {
      var ЗОЛОТОЙ = Math.PI * (3 - Math.sqrt(5));
      var i, j;
      for (i = 0; i < ВСЕГО; i++) {
        var a = i * ЗОЛОТОЙ, б = Math.sqrt((i + 0.6) / ВСЕГО);
        ТОЧКИ.push({ a: a, ко: Math.cos(a), си: Math.sin(a),
                     x: Math.cos(a) * б, y: Math.sin(a) * б });
      }

      for (i = 0; i < ВСЕГО; i++) {
        var лучш = -1, дист = 1e9;
        for (j = 0; j < i; j++) {
          var dx = ТОЧКИ[i].x - ТОЧКИ[j].x, dy = ТОЧКИ[i].y - ТОЧКИ[j].y;
          var d = dx * dx + dy * dy;
          if (d < дист) { дист = d; лучш = j; }
        }
        РОДИТЕЛЬ.push(лучш);
      }
      for (i = 0; i < ВСЕГО; i++) ВЕС.push(1);
      for (i = ВСЕГО - 1; i > 0; i--) {
        var р = РОДИТЕЛЬ[i];
        if (р >= 0) ВЕС[р] += ВЕС[i];
      }
    })();

    function долиR(i, n) {

      var м = Math.max(МАЛО, n);
      var к = 0.56 + 0.44 * Math.sqrt(м / ВСЕГО);
      return Math.sqrt((i + 0.6) / м) * к;
    }

    function радиусРубежа(предел, n) {
      return Math.min(1.04, долиR(предел - 1, Math.max(1, n)));
    }

    var ЦИКЛ = 21.0;

    function сколько(t) {
      var с = t < 0 ? 18 : t % ЦИКЛ, р;

      if (с < 2.6) р = { nт: МАЛО * плавно(с / 2.6), ступень: 0 };
      else if (с < 4.6) р = { nт: МАЛО, ступень: 0, держим: 1 };
      else if (с < 11.6) р = { nт: МАЛО + (ВСЕГО - МАЛО) * плавно((с - 4.6) / 7),
                               ступень: 1 };
      else if (с < 13.6) р = { nт: ВСЕГО, ступень: 1, держим: 1 };
      else if (с < 19) р = { nт: ВСЕГО, ступень: 2, держим: 1 };
      else р = { nт: ВСЕГО, ступень: 2, уход: плавно((с - 19) / 2) };
      р.n = Math.round(р.nт);
      return р;
    }

    крутить(к, function (t) {
      var Ш = к.ш(), В = к.в(), s = сколько(t);
      ctx.clearRect(0, 0, Ш, В);
      ctx.globalAlpha = 1 - (s.уход || 0);

      var поля = 16, зазор = 22;
      var доступно = Ш - поля * 2;
      var R = Math.min(В * 0.42, доступно * 0.22);
      var шСети = R * 2.5;
      var шКарт = Math.max(215, Math.min(320, Ш * 0.26));
      var шСчёта = Math.max(150, Math.min(210, Ш * 0.16));
      function ширина() {
        return шКарт + зазор + шСети + (шСчёта ? зазор + шСчёта : 0);
      }
      if (ширина() > доступно) шСчёта = 0;
      if (ширина() > доступно) {
        шКарт = Math.max(150, шКарт - (ширина() - доступно));
      }
      if (ширина() > доступно) {
        R = Math.max(60, R - (ширина() - доступно) / 2.5);
        шСети = R * 2.5;
      }
      var всего = ширина();
      var x0 = Math.max(поля, (Ш - всего) / 2);

      карточкиТарифов(ctx, x0, поля, шКарт, В - поля * 2, s, t, !шСчёта);
      var cx = x0 + шКарт + зазор + шСети / 2, cy = В * 0.52;
      сеть(ctx, cx, cy, R, s, t);
      if (шСчёта) {
        счёт(ctx, x0 + шКарт + зазор + шСети + зазор, поля, шСчёта,
             В - поля * 2, s);
      }
      ctx.globalAlpha = 1;
    });

    function карточкиТарифов(ctx, x, y, ш, в, s, t, соСчётом) {

      var сверху = соСчётом ? 74 : 0;
      var вК = Math.min(78, (в - сверху - 2) / 3 - 8);
      var y0 = y + сверху + (в - сверху - (вК * 3 + 16)) / 2;
      if (соСчётом) {
        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";
        ctx.font = "700 40px " + МОНО;
        ctx.fillStyle = П.чернила;
        ctx.fillText(чис(s.n), x + 2, y + 40);
        ctx.font = "600 11.5px " + ШРИФТ;
        ctx.fillStyle = П.тихий;
        ctx.fillText(С("потребителей в схеме"), x + 2, y + 58);
      }

      for (var i = 0; i < РУБЕЖ.length; i++) {
        var р = РУБЕЖ[i], yК = y0 + i * (вК + 8);
        var активен = i === s.ступень, пройден = i < s.ступень;
        var цв = i === 2 ? П.добро : П.акцент;
        карточка(ctx, x, yК, ш, вК, 10,
                 активен ? (П.тьма ? "rgba(76,123,255,.10)" : "rgba(19,72,224,.05)")
                         : П.бумага,
                 активен ? цв : П.линия);
        ctx.globalAlpha = (активен ? 1 : пройден ? .72 : .42) *
                          (1 - (s.уход || 0));

        ctx.beginPath();
        ctx.arc(x + 16, yК + 20, активен ? 5.5 : 4.5, 0, Math.PI * 2);
        ctx.fillStyle = цв;
        ctx.fill();

        var справа = i === 2 ? чис(ВСЕГО) + " + " + С("эпюра и годовые потери")
                             : чис(Math.min(s.n, р.n)) + " / " + чис(р.n);
        ctx.font = "600 11.5px " + МОНО;
        var шСправа = ctx.measureText(справа).width;
        ctx.font = (активен ? "700 13.5px " : "600 13px ") + ШРИФТ;
        var шИмени = ctx.measureText(С(р.имя)).width;
        var водну = 28 + шИмени + 14 + шСправа + 12 <= ш;
        ctx.fillStyle = активен ? П.чернила : П.тихий;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(влезает(ctx, С(р.имя), ш - 40),
                     x + 28, yК + (водну ? 20 : 17));
        ctx.font = "600 11.5px " + МОНО;
        ctx.fillStyle = П.тихий;
        if (водну) {
          ctx.textAlign = "right";
          ctx.fillText(справа, x + ш - 12, yК + 20);
        } else {
          ctx.textAlign = "left";
          ctx.fillText(влезает(ctx, справа, ш - 40), x + 28, yК + 34);
        }

        var xП = x + 14, шП = ш - 28, yП = yК + вК - 18;
        путьСкругл(ctx, xП, yП, шП, 6, 3);
        ctx.fillStyle = П.линия;
        ctx.fill();
        var доля2 = i === 2
          ? (s.ступень === 2 ? 1 : 0)
          : Math.min(1, s.nт / р.n);
        if (доля2 > 0) {
          путьСкругл(ctx, xП, yП, Math.max(6, шП * доля2), 6, 3);
          ctx.fillStyle = цв;
          ctx.fill();
        }

        if (пройден || (активен && i < 2 && s.n >= р.n)) {
          ctx.font = "600 9.5px " + ШРИФТ;
          ctx.fillStyle = цв;
          ctx.textAlign = "right";
          ctx.textBaseline = "bottom";
          ctx.fillText(С("предел достигнут"), x + ш - 12, yП - 3);
        }
        ctx.globalAlpha = 1 - (s.уход || 0);
      }
    }

    function счёт(ctx, x, y, ш, в, s) {
      var текущий = РУБЕЖ[s.ступень];
      var цв = s.ступень === 2 ? П.добро : П.акцент;
      var yЦ = y + в / 2;
      ctx.textAlign = "right";
      ctx.textBaseline = "alphabetic";
      ctx.font = "700 " + Math.min(64, ш * 0.34) + "px " + МОНО;
      ctx.fillStyle = П.чернила;
      var сч = чис(s.n);
      ctx.fillText(сч, x + ш, yЦ - 4);
      ctx.font = "600 12px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.fillText(влезает(ctx, С("потребителей в схеме"), ш),
                   x + ш, yЦ + 16);
      ctx.font = "700 12.5px " + ШРИФТ;
      ctx.fillStyle = цв;
      ctx.fillText(влезает(ctx, С(текущий.имя), ш), x + ш, yЦ + 42);
      if (s.ступень < 2 && s.n >= текущий.n) {
        ctx.font = "600 10.5px " + ШРИФТ;
        ctx.fillStyle = П.тихий;
        ctx.fillText(влезает(ctx, С("предел достигнут"), ш), x + ш, yЦ + 60);
      }
    }

    function сеть(ctx, cx, cy, R, s, t) {

      var nт = Math.max(0.001, s.nт);
      var предел = Math.min(ТОЧКИ.length, Math.ceil(nт));
      function точка(i) {
        var д = долиR(i, nт) * R;
        return { x: cx + ТОЧКИ[i].ко * д, y: cy + ТОЧКИ[i].си * д };
      }

      function проявление(i) {
        return Math.max(0, Math.min(1, nт - i));
      }
      var i;

      for (i = 1; i < предел; i++) {
        var п2 = проявление(i);
        if (п2 <= 0) continue;
        var a = точка(i), b = точка(РОДИТЕЛЬ[i]);
        ctx.strokeStyle = i < МАЛО ? П.акцент : П.акцентС;
        ctx.globalAlpha = (1 - (s.уход || 0)) * п2 *
                          (i < МАЛО ? .8 : .55);
        ctx.lineWidth = Math.max(0.6, Math.min(3.4, Math.sqrt(ВЕС[i]) * 0.30));
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(b.x, b.y);
        ctx.lineTo(b.x + (a.x - b.x) * п2, b.y + (a.y - b.y) * п2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1 - (s.уход || 0);

      for (i = 0; i < предел; i++) {
        var п3 = проявление(i);
        if (п3 <= 0) continue;
        var т = точка(i);
        var св = i < МАЛО ? П.акцент : П.акцентС;
        var р2 = (i < МАЛО ? 3.6 : 2.2) * (0.4 + 0.6 * п3);
        ctx.globalAlpha = (1 - (s.уход || 0)) * п3;
        ctx.beginPath();
        ctx.arc(т.x, т.y, р2, 0, Math.PI * 2);
        ctx.fillStyle = св;
        ctx.fill();
      }
      ctx.globalAlpha = 1 - (s.уход || 0);

      ctx.beginPath();
      ctx.arc(cx, cy, 14, 0, Math.PI * 2);
      ctx.fillStyle = П.тьма ? "#22304d" : "#ffffff";
      ctx.fill();
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = П.акцент;
      ctx.font = "700 10.5px " + ШРИФТ;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(С("ТП"), cx, cy);

      for (i = 0; i < РУБЕЖ.length; i++) {
        var р3 = РУБЕЖ[i];
        if (i > s.ступень) continue;

        var последний = i === РУБЕЖ.length - 1;
        var рад = радиусРубежа(р3.n, s.nт) * R + (последний ? 14 : 5);
        if (последний) рад = Math.min(рад, R * 1.04) * (0.97 + 0.03 *
          Math.sin((t < 0 ? 0 : t) * 1.6));
        var активный = i === s.ступень;
        var цв2 = последний ? П.добро : П.акцент;
        ctx.setLineDash(последний ? [2, 5] : [6, 5]);
        ctx.strokeStyle = цв2;
        ctx.globalAlpha = (1 - (s.уход || 0)) * (активный ? .85 : .40);
        ctx.lineWidth = активный ? 1.7 : 1;
        ctx.beginPath();
        ctx.arc(cx, cy, рад, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        var текст = С(р3.имя) + (последний ? " · " + С("эпюра и годовые потери") : " · " + чис(р3.n));
        ctx.font = "700 10px " + ШРИФТ;
        var шТ = ctx.measureText(текст).width + 12;

        var уголП = [-Math.PI / 2, -Math.PI / 2 + 2.3, -Math.PI / 2 - 2.3][i];
        var отступ = рад < 54 ? 54 - рад : 0;
        var xТ = cx + Math.cos(уголП) * (рад + отступ);
        var yТ = cy + Math.sin(уголП) * (рад + отступ);
        if (отступ > 0) {
          ctx.strokeStyle = цв2;
          ctx.globalAlpha = (1 - (s.уход || 0)) * .35;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(уголП) * рад, cy + Math.sin(уголП) * рад);
          ctx.lineTo(xТ, yТ);
          ctx.stroke();
        }
        ctx.globalAlpha = (1 - (s.уход || 0)) * (активный ? 1 : .55);
        путьСкругл(ctx, xТ - шТ / 2, yТ - 8, шТ, 16, 8);
        ctx.fillStyle = П.поле;
        ctx.fill();
        ctx.strokeStyle = цв2;
        ctx.lineWidth = 1;
        ctx.globalAlpha = (1 - (s.уход || 0)) * (активный ? .8 : .35);
        ctx.stroke();
        ctx.globalAlpha = (1 - (s.уход || 0)) * (активный ? 1 : .6);
        ctx.fillStyle = цв2;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(текст, xТ, yТ + 0.5);
        ctx.globalAlpha = 1 - (s.уход || 0);
      }
    }
  }

  function конвейер() {
    var к = холст("anim-pipeline");
    if (!к) return;
    var ctx = к.ctx;

    var СТАНЦИИ = [
      { имя: "Окно объекта",    что: "проверяет поля" },
      { имя: "Редактор",        что: "ставит координаты" },
      { имя: "Справочник",      что: "разбирает марки" },
      { имя: "Схема замещения", что: "узлы и ветви" },
      { имя: "Расчёт",          что: "считает и проверяет" }
    ];

    var СПРАВОЧНИК = ["СИП-4 4×16", "СИП-4 4×25", "СИП-4 4×35",
                      "СИП-4 4×50", "СИП-4 4×70"];
    var ПРОХОД = [
      {
        фраза: "опора от 1/3 и три потребителя по 5 кВт",
        ярлык: "опора 1/3, три потребителя по 5 кВт",
        марка: "СИП-4 4×35",
        шаги: [{ ключ: "поля верны", знач: "опора 1/3, три потребителя по 5 кВт" },
               { ключ: "координаты расставлены", знач: null },
               { ключ: "марка разобрана", знач: "СИП-4 4×35" },
               { ключ: "узлов 9, ветвей 8", знач: null },
               { ключ: "Umin", знач: null }],
        до: 5, итог: "схема рассчитана", удача: true
      },
      {
        фраза: "потребитель с cos φ = 0",
        ярлык: "cos φ = 0",
        марка: null,
        шаги: [{ ключ: "окно не принимает", знач: "cos φ = 0" }],
        до: 1, итог: "схема не изменилась", удача: false
      }
    ];
    var ШАГС = 2.6, ИТОГ = 2.8;
    var ДЛИНА = ПРОХОД.map(function (п) { return п.до * ШАГС + ИТОГ; });
    var ЦИКЛ = ДЛИНА[0] + ДЛИНА[1];

    function состояние(t) {
      if (t < 0) return { п: 1, шаг: 2, доля: 1, итог: 1 };
      var с = t % ЦИКЛ;
      var п = с < ДЛИНА[0] ? 0 : 1;
      var в = п ? с - ДЛИНА[0] : с;
      var шаг = Math.min(ПРОХОД[п].до - 1, Math.floor(в / ШАГС));
      var внутри = (в - шаг * ШАГС) / ШАГС;
      var итог = в > ПРОХОД[п].до * ШАГС
        ? плавно((в - ПРОХОД[п].до * ШАГС) / 0.8) : 0;
      return { п: п, шаг: шаг, доля: внутри, итог: итог };
    }

    крутить(к, function (t) {
      var Ш = к.ш(), В = к.в(), s = состояние(t), i;
      var пр = ПРОХОД[s.п];

      var виден = (s.доля < 0.34 && s.шаг > 0) ? s.шаг - 1 : s.шаг;
      var отказ = !пр.удача && виден >= пр.до - 1;
      ctx.clearRect(0, 0, Ш, В);

      var поля = Math.max(14, Ш * 0.022);
      var узко = Ш < 720;

      var шМини = узко ? 0 : Math.max(132, Math.min(190, Ш * 0.145));
      var xМини = Ш - поля - шМини;
      var шПояс = (шМини ? xМини - 12 : Ш - поля) - поля;

      var зазор = Math.max(7, шПояс * 0.014);
      var шБ = (шПояс - зазор * 4) / 5;
      var вБ = 58;
      var вГруппы = 180;
      var верх = Math.max(6, (В - вГруппы) / 2);
      var yФразы = верх;
      var yЗоны = верх + 52;
      var yБ = верх + 58;
      var yТокен = верх + 132;
      var yСправ = верх + 158;
      function бокс(i) { return поля + (шБ + зазор) * i; }

      function зона(от, до, подпись, цвет, фон) {
        var x = бокс(от) - 8, ш = бокс(до) + шБ + 8 - x;
        путьСкругл(ctx, x, yБ - 8, ш, вБ + 24, 12);
        ctx.fillStyle = фон;
        ctx.fill();
        ctx.font = "700 9.5px " + ШРИФТ;
        ctx.textAlign = "left";
        ctx.textBaseline = "bottom";
        ctx.fillStyle = цвет;
        ctx.fillText(влезает(ctx, подпись.toUpperCase(), ш - 16),
                     x + 11, yЗоны);
      }
      зона(0, 1, С("редактор схемы"), П.акцент, П.мягкийА);
      зона(2, 4, С("расчётное ядро"), П.добро, П.мягкийД);

      var xШов = (бокс(1) + шБ + бокс(2)) / 2;
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = П.тихий;
      ctx.globalAlpha = .55;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(xШов, yБ - 8);
      ctx.lineTo(xШов, yБ + вБ + 16);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.globalAlpha = 1;

      for (i = 0; i < СТАНЦИИ.length; i++) {
        var x = бокс(i);
        var пройден = i < s.шаг || (s.итог > 0 && i < пр.до);
        var текущий = i === s.шаг && s.итог === 0;
        var плохой = отказ && i === пр.до - 1;
        var цв = плохой ? П.беда : (i < 2 ? П.акцент : П.добро);
        ctx.globalAlpha = (пройден || текущий) ? 1 : .45;
        путьСкругл(ctx, x, yБ, шБ, вБ, 10);
        ctx.fillStyle = текущий || плохой
          ? (П.тьма ? "rgba(23,35,60,.98)" : "rgba(255,255,255,.99)")
          : (П.тьма ? "rgba(18,27,46,.75)" : "rgba(255,255,255,.80)");
        ctx.fill();
        ctx.strokeStyle = (текущий || плохой) ? цв : П.линия;
        ctx.lineWidth = (текущий || плохой) ? 1.8 : 1;
        ctx.stroke();
        ctx.textAlign = "center";
        ctx.textBaseline = "alphabetic";
        ctx.font = "700 12.5px " + ШРИФТ;
        ctx.fillStyle = (текущий || плохой) ? цв : П.чернила;
        ctx.fillText(влезает(ctx, С(СТАНЦИИ[i].имя), шБ - 10), x + шБ / 2, yБ + 24);
        ctx.font = "500 10px " + ШРИФТ;
        ctx.fillStyle = П.тихий;
        ctx.fillText(влезает(ctx, С(СТАНЦИИ[i].что), шБ - 10),
                     x + шБ / 2, yБ + 40);

        if (текущий) {
          var шП = шБ - 22;
          путьСкругл(ctx, x + 11, yБ + вБ - 9, шП, 3, 1.5);
          ctx.fillStyle = П.линия;
          ctx.fill();
          путьСкругл(ctx, x + 11, yБ + вБ - 9,
                     Math.max(3, шП * Math.min(1, s.доля / 0.9)), 3, 1.5);
          ctx.fillStyle = цв;
          ctx.fill();
        }
        ctx.globalAlpha = 1;

        if (i < СТАНЦИИ.length - 1) {
          var xс = x + шБ, y2 = yБ + вБ / 2;
          ctx.strokeStyle = i < s.шаг ? (i < 1 ? П.акцент : П.добро) : П.линия2;
          ctx.globalAlpha = i < s.шаг ? .9 : .5;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(xс + 1, y2);
          ctx.lineTo(xс + зазор - 1, y2);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(xс + зазор - 5, y2 - 3);
          ctx.lineTo(xс + зазор - 1, y2);
          ctx.lineTo(xс + зазор - 5, y2 + 3);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      var xт = бокс(s.шаг) + шБ / 2;
      if (s.доля < 0.34 && s.шаг > 0) {
        var пред = бокс(s.шаг - 1) + шБ / 2;
        xт = пред + (xт - пред) * плавно(s.доля / 0.34);
      }
      if (s.итог > 0 && отказ) {
        xт = xт - (xт - (бокс(0) + шБ / 2)) * s.итог;
      }
      var yт = yТокен;
      ctx.font = "600 10px " + МОНО;
      var ярлык = влезает(ctx, С(пр.ярлык), шБ * 2.4);
      var шЯ = ctx.measureText(ярлык).width + 26;

      xт = Math.max(поля + шЯ / 2, Math.min(поля + шПояс - шЯ / 2, xт));
      путьСкругл(ctx, xт - шЯ / 2, yт - 10, шЯ, 21, 10.5);
      ctx.fillStyle = отказ ? П.мягкийБ : П.мягкийА;
      ctx.fill();
      ctx.strokeStyle = отказ ? П.беда : П.акцент;
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.fillStyle = отказ ? П.беда : П.акцент;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(ярлык, xт - шЯ / 2 + 19, yт + 1);
      ctx.beginPath();
      ctx.arc(xт - шЯ / 2 + 10, yт + 0.5,
              4.4 + (отказ ? 0 : 1.1 * Math.sin((t < 0 ? 0 : t) * 6)),
              0, Math.PI * 2);
      ctx.fillStyle = отказ ? П.беда : П.акцент;
      ctx.fill();

      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      плашка(ctx, поля, yФразы, "› " + С(пр.фраза), П.поле,
             П.тьма ? "rgba(76,123,255,.92)" : "rgba(19,72,224,.94)");

      var ш2 = пр.шаги[Math.min(виден, пр.шаги.length - 1)];
      var текст;
      if (s.итог > 0) {
        текст = С(пр.итог);
      } else if (ш2.ключ === "Umin") {
        текст = "Umin " + чис(219.4, 1) + " " + С("В") + " · " + С("связность ОК");
      } else {
        текст = С(ш2.ключ) + (ш2.знач ? ": " + С(ш2.знач) : "");
      }
      var цвет2 = отказ ? П.беда
        : (s.итог > 0 ? П.добро : (виден < 2 ? П.акцент : П.добро));
      плашка(ctx, поля + шПояс, yФразы, влезает(ctx, текст, шПояс * 0.45),
             П.поле, цвет2, true);

      var сверка = пр.до >= 3 && ((виден >= 2 && s.итог === 0) || (отказ && s.итог > 0));
      if (сверка) {
        справочник(ctx, бокс(2) - 8, yСправ,
                   Math.min(шПояс - (бокс(2) - 8 - поля),
                            шБ * 3 + зазор * 2 + 16),
                   пр.марка, отказ);
      }

      if (шМини) {
        мини(ctx, xМини, верх + 14, шМини, 150, s, пр, отказ);
      }
    });

    function справочник(ctx, x, y, ш, марка, отказ) {
      ctx.font = "700 8.5px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      var подпись = С("справочник марок").toUpperCase();
      ctx.fillText(подпись, x + 2, y + 9);
      var xЧ = x + 4 + ctx.measureText(подпись).width + 10;

      var список = отказ ? [марка].concat(СПРАВОЧНИК) : СПРАВОЧНИК.slice();
      ctx.font = "600 9.5px " + МОНО;
      for (var i = 0; i < список.length; i++) {
        var имя = список[i];
        var есть = имя === марка && !отказ;
        var нет = отказ && i === 0;
        var знак = есть ? "✓ " : (нет ? "✗ " : "");
        var шФ = ctx.measureText(знак + имя).width + 14;
        if (xЧ + шФ > x + ш) break;
        путьСкругл(ctx, xЧ, y, шФ, 19, 9.5);
        ctx.fillStyle = есть ? П.мягкийД : (нет ? П.мягкийБ : "transparent");
        if (есть || нет) ctx.fill();
        ctx.strokeStyle = есть ? П.добро : (нет ? П.беда : П.линия);
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = есть ? П.добро : (нет ? П.беда : П.тихий);
        ctx.globalAlpha = (есть || нет) ? 1 : .7;
        ctx.fillText(знак + имя, xЧ + 7, y + 10);
        ctx.globalAlpha = 1;
        xЧ += шФ + 5;
      }
    }

    function мини(ctx, x, y, ш, в, s, пр, отказ) {
      карточка(ctx, x, y, ш, в, 11, П.бумага, П.линия);
      ctx.font = "700 9px " + ШРИФТ;
      ctx.fillStyle = П.тихий;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(С("схема").toUpperCase(), x + 10, y + 8);

      var принято = пр.удача && s.итог > 0;
      var xл = x + 16, xп = x + ш - 16, yл = y + в * 0.46;
      ctx.strokeStyle = П.акцент;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(xл, yл);
      ctx.lineTo(xп, yл);
      ctx.stroke();
      var шагM = (xп - xл) / 3;
      for (var i = 0; i <= 3; i++) {
        var xо = xл + шагM * i;
        var новый = i === 3;
        if (новый && !принято) continue;
        ctx.beginPath();
        ctx.arc(xо, yл, 3.4, 0, Math.PI * 2);
        ctx.fillStyle = П.поле;
        ctx.fill();
        ctx.strokeStyle = новый ? П.добро : П.акцент;
        ctx.lineWidth = 1.8;
        ctx.stroke();

        var сколькоД = новый ? 3 : 1;
        for (var j = 0; j < сколькоД; j++) {
          var xд = xо + (сколькоД === 1 ? 0 : (j - 1) * 12);
          ctx.strokeStyle = новый ? П.добро : П.акцентС;
          ctx.globalAlpha = .8;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(xо, yл);
          ctx.lineTo(xд, yл + 20);
          ctx.stroke();
          ctx.globalAlpha = 1;
          домик(ctx, xд, yл + 30, 9,
                новый ? П.добро : (П.тьма ? "#6c7ea6" : "#c3cde2"));
        }
      }

      var подпись = s.итог > 0 ? С(пр.итог) : "";
      if (подпись) {
        ctx.font = "600 9.5px " + ШРИФТ;
        ctx.fillStyle = отказ ? П.беда : П.добро;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(влезает(ctx, подпись, ш - 16), x + ш / 2, y + в - 9);
      }
    }
  }

  function пуск() { эпюра(); стройка(); тарифы(); конвейер(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", пуск);
  } else {
    пуск();
  }
})();
