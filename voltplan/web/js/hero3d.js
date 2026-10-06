(function () {
  "use strict";
  function язык() {
    if (window.VOLTPLAN_SCENE_LANG) return window.VOLTPLAN_SCENE_LANG;
    try { return localStorage.getItem("voltplan-language") || "ru"; }
    catch (e) { return "ru"; }
  }
  var ХОЛСТ = document.getElementById("hero3d");
  if (!ХОЛСТ || !ХОЛСТ.getContext) return;

  var ctx = ХОЛСТ.getContext("2d");
  var тише = window.matchMedia &&
             window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var П = null;

  function палитра() {
    var тьма = document.documentElement.getAttribute("data-theme") === "dark";
    return тьма ? {
      тьма:      true,
      горизонт:  [16, 26, 46],
      небо:      [86, 116, 176],
      отражение: [26, 34, 54],
      земля:     [7, 12, 23],
      сетка:     [122, 160, 255],
      тень:      [0, 0, 0],
      силаТени:  0.50,
      бетон:     { цвет: [126, 137, 160], блеск: 0.05 },
      бетонТ:    { цвет: [104, 114, 136], блеск: 0.04 },
      металл:    { цвет: [138, 152, 180], блеск: 0.55 },
      корпус:    { цвет: [168, 182, 212], блеск: 0.14 },
      цоколь:    { цвет: [96, 106, 128], блеск: 0.04 },
      кровляТП:  { цвет: [70, 84, 116], блеск: 0.18 },
      стена:     { цвет: [158, 170, 196], блеск: 0.06 },
      кровля:    { цвет: [72, 96, 150], блеск: 0.20 },
      окно:      { цвет: [126, 172, 255], блеск: 0.85 },
      дверь:     { цвет: [66, 80, 108], блеск: 0.12 },
      изолятор:  { цвет: [110, 168, 245], блеск: 0.70 },
      провод:    [150, 168, 205],
      импульс:   [126, 176, 255],
      подпись:   [190, 210, 255]
    } : {
      тьма:      false,
      горизонт:  [225, 232, 244],
      небо:      [206, 224, 255],
      отражение: [178, 186, 202],
      земля:     [10, 18, 32],
      сетка:     [19, 72, 224],
      тень:      [30, 44, 76],
      силаТени:  0.34,
      бетон:     { цвет: [173, 182, 201], блеск: 0.05 },
      бетонТ:    { цвет: [152, 162, 183], блеск: 0.04 },
      металл:    { цвет: [150, 162, 186], блеск: 0.55 },
      корпус:    { цвет: [232, 238, 249], блеск: 0.14 },
      цоколь:    { цвет: [178, 187, 204], блеск: 0.04 },
      кровляТП:  { цвет: [104, 121, 155], блеск: 0.18 },
      стена:     { цвет: [238, 242, 249], блеск: 0.06 },
      кровля:    { цвет: [56, 79, 134], блеск: 0.22 },
      окно:      { цвет: [104, 152, 226], блеск: 0.85 },
      дверь:     { цвет: [92, 108, 138], блеск: 0.12 },
      изолятор:  { цвет: [96, 154, 236], блеск: 0.70 },
      провод:    [52, 68, 102],
      импульс:   [19, 72, 224],
      подпись:   [19, 72, 224]
    };
  }
  П = палитра();
  new MutationObserver(function () { П = палитра(); })
    .observe(document.documentElement,
             { attributes: true, attributeFilter: ["data-theme"] });

  var ОПОРЫ = [];
  var ПРОВОДА = [];
  var ДОМА = [];
  var ТП = { x: 0, z: 0, ш: 7.4, г: 5.0, в: 4.5 };

  function опора(x, z, h) {
    var о = { x: x, z: z, h: h };
    ОПОРЫ.push(о);
    return о;
  }

  function крепление(о, сторона) {
    return { x: о.x, y: о.h - 0.55, z: о.z + сторона * 1.35 };
  }

  function выводТП(сторона) {
    return { x: ТП.x + сторона * 1.5, y: ТП.в + 1.15, z: ТП.z };
  }

  function фидер(градусы, сколько, длина, домаНа) {

    var a = градусы * Math.PI / 180;
    var шагX = Math.cos(a) * длина, шагZ = Math.sin(a) * длина;
    var нx = -Math.sin(a), нz = Math.cos(a);
    var пред = null, x = ТП.x, z = ТП.z, первый = true;
    for (var i = 0; i < сколько; i++) {
      x += шагX + (i === 0 ? шагX * 0.35 : 0);
      z += шагZ + (i === 0 ? шагZ * 0.35 : 0);
      var о = опора(x, z, 8.6 + (i % 3) * 0.45);
      if (первый) {
        var с = (шагX >= 0) ? 1 : -1;

        ПРОВОДА.push({ a: выводТП(с), b: крепление(о, -1), уровень: i,
                       импульс: true });
        ПРОВОДА.push({ a: выводТП(с), b: крепление(о, 1), уровень: i });
        первый = false;
      } else {
        ПРОВОДА.push({ a: крепление(пред, -1), b: крепление(о, -1), уровень: i,
                       импульс: true });
        ПРОВОДА.push({ a: крепление(пред, 1), b: крепление(о, 1), уровень: i });
      }

      if (домаНа.indexOf(i) >= 0) {
        var сторона = (i % 2 === 0) ? 1 : -1;
        var д = {
          x: о.x + нx * 7.6 * сторона,
          z: о.z + нz * 7.6 * сторона,
          ш: 3.6, г: 3.0, в: 2.7,
          пов: Math.atan2(нz * сторона, нx * сторона)
        };
        ДОМА.push(д);
        ПРОВОДА.push({
          a: крепление(о, сторона),
          b: { x: д.x - нx * д.г * 0.5 * сторона,
               y: д.в + 0.5,
               z: д.z - нz * д.г * 0.5 * сторона },
          ввод: true, уровень: i + 1, импульс: true
        });
      }
      пред = о;
    }
  }

  фидер(18, 5, 9.2, [1, 3]);
  фидер(88, 4, 9.0, [0, 2]);
  фидер(152, 5, 9.2, [1, 3]);
  фидер(222, 4, 9.0, [1, 3]);
  фидер(296, 4, 9.0, [0, 2]);

  var РАДИУС = (function () {
    var м = 0;
    for (var i = 0; i < ОПОРЫ.length; i++) {
      м = Math.max(м, Math.hypot(ОПОРЫ[i].x, ОПОРЫ[i].z));
    }
    for (var j = 0; j < ДОМА.length; j++) {
      м = Math.max(м, Math.hypot(ДОМА[j].x, ДОМА[j].z));
    }
    return м + 9;
  })();

  var УГОЛ0 = -0.62, наклонY = 0.46, угол = УГОЛ0;
  var мышьX = 0, мышьY = 0, целX = 0, целY = 0;
  var масштаб = 1, сдвигX = 0, сдвигY = 0;

  var СВЕТ = (function (x, y, z) {
    var д = Math.sqrt(x * x + y * y + z * z);
    return { x: x / д, y: y / д, z: z / д };
  })(-0.46, 0.72, -0.52);

  var ЗАПОЛН = { x: 0.62, y: 0.28, z: 0.73 };

  var _син = 0, _кос = 1, _синН = 0, _косН = 1;
  function обновитьКамеру() {
    var а = угол + целX * 0.42, н = наклонY + целY * 0.09;
    _син = Math.sin(а); _кос = Math.cos(а);
    _синН = Math.sin(н); _косН = Math.cos(н);
  }

  function сырое(x, y, z) {
    var с = _син, к = _кос;
    var X = x * к - z * с;
    var Z = x * с + z * к;

    var Y = y * _косН + Z * _синН;

    var глубина = Z * _косН - y * _синН + 128;
    var f = 940 / Math.max(20, глубина);
    return { X: X * f, Y: -Y * f, f: f, глубина: глубина };
  }

  function подогнать(w, h) {

    var лx = 1e9, пx = -1e9, вy = 1e9, нy = -1e9;
    function учесть(x, y, z) {
      var т = сырое(x, y, z);
      if (т.X < лx) лx = т.X;
      if (т.X > пx) пx = т.X;
      if (т.Y < вy) вy = т.Y;
      if (т.Y > нy) нy = т.Y;
    }
    for (var i = 0; i < ОПОРЫ.length; i++) {
      учесть(ОПОРЫ[i].x, 0, ОПОРЫ[i].z);
      учесть(ОПОРЫ[i].x, ОПОРЫ[i].h + 0.4, ОПОРЫ[i].z);
    }
    for (var j = 0; j < ДОМА.length; j++) {
      учесть(ДОМА[j].x - ДОМА[j].ш, 0, ДОМА[j].z - ДОМА[j].г);
      учесть(ДОМА[j].x + ДОМА[j].ш, ДОМА[j].в + 1.8, ДОМА[j].z + ДОМА[j].г);
    }
    учесть(ТП.x, ТП.в + 1.8, ТП.z);
    var ширина = Math.max(1, пx - лx), высота = Math.max(1, нy - вy);
    масштаб = Math.min(w * 0.95 / ширина, h * 0.90 / высота);
    сдвигX = w / 2 - (лx + пx) / 2 * масштаб;
    сдвигY = h * 0.50 - (вy + нy) / 2 * масштаб;
  }

  function точка(x, y, z) {
    var с = сырое(x, y, z);
    return { X: сдвигX + с.X * масштаб, Y: сдвигY + с.Y * масштаб,
             f: с.f * масштаб, глубина: с.глубина };
  }

  var _цвета = new Map();
  function цвет(rgb, a) {
    var r = rgb[0] | 0, g = rgb[1] | 0, b = rgb[2] | 0;
    var ак = Math.round(Math.max(0.02, Math.min(1, a)) * 100);
    var ключ = (r << 24) ^ (g << 16) ^ (b << 8) ^ ак;
    var есть = _цвета.get(ключ);
    if (есть !== undefined) return есть;
    var с = "rgba(" + r + "," + g + "," + b + "," + (ак / 100) + ")";
    if (_цвета.size > 4000) _цвета.clear();
    _цвета.set(ключ, с);
    return с;
  }

  function смешать(a, b, t) {
    t = Math.max(0, Math.min(1, t));
    return [a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t];
  }

  function освещение(н, блеск) {
    var верх = 0.5 + 0.5 * н.y;
    var ключ = Math.max(0, н.x * СВЕТ.x + н.y * СВЕТ.y + н.z * СВЕТ.z);
    var зап = Math.max(0, н.x * ЗАПОЛН.x + н.y * ЗАПОЛН.y + н.z * ЗАПОЛН.z);
    var I = 0.30 + 0.26 * верх + 0.60 * ключ + 0.15 * зап;
    var блик = (блеск || 0) * Math.pow(ключ, 22) * 0.85;
    return { I: I, блик: блик, небо: верх };
  }

  function тонировать(мат, н, глубина) {
    var с = освещение(н, мат.блеск);
    var базовый = мат.цвет;

    var окружение = смешать(П.отражение, П.небо, с.небо);
    var т = смешать(базовый, окружение, 0.16 + 0.18 * мат.блеск);
    т = [т[0] * с.I, т[1] * с.I, т[2] * с.I];
    if (с.блик > 0) {
      т = смешать(т, [255, 255, 255], Math.min(0.7, с.блик));
    }

    var д = Math.max(0, Math.min(1, (глубина - 96) / 150));
    return смешать(т, П.горизонт, д * 0.62);
  }

  var ГРАНИ = [], ТЕНИ = [], _граней = 0;
  var _зап_x = new Float64Array(8), _зап_y = new Float64Array(8);

  function виднаЛи(точки, нормаль) {

    if (!нормаль) return true;
    return (нормаль.x * _син + нормаль.z * _кос) * _косН
           - нормаль.y * _синН < 0;
  }

  function норм(н) {
    var д = Math.sqrt(н.x * н.x + н.y * н.y + н.z * н.z) || 1;
    return { x: н.x / д, y: н.y / д, z: н.z / д };
  }

  function грань(точки, мат, нормаль, прозрачность) {
    if (!виднаЛи(точки, нормаль)) return;
    var n = точки.length;
    var кx = _зап_x, кy = _зап_y;
    if (кx.length < n) { кx = _зап_x = new Float64Array(n * 2);
                         кy = _зап_y = new Float64Array(n * 2); }
    var глубина = 0;
    for (var i = 0; i < n; i++) {
      var т = точки[i];
      var п = точка(т.x, т.y, т.z);
      кx[i] = п.X; кy[i] = п.Y;
      глубина += п.глубина;
    }
    глубина /= n;
    var нн = нормаль ? норм(нормаль) : { x: 0, y: 1, z: 0 };
    var тон = тонировать(мат, нн, глубина);

    var г = ГРАНИ[_граней];
    if (!г) { г = ГРАНИ[_граней] = { x: [], y: [] }; }
    г.глубина = глубина;
    г.n = n;
    for (i = 0; i < n; i++) { г.x[i] = кx[i]; г.y[i] = кy[i]; }
    г.заливка = цвет(тон, прозрачность === undefined ? 1 : прозрачность);
    г.кромка = цвет([тон[0] * 0.82, тон[1] * 0.82, тон[2] * 0.86], 0.55);
    г.свой = null;
    _граней++;
  }

  function своё(глубина, рисовать) {
    var г = ГРАНИ[_граней];
    if (!г) { г = ГРАНИ[_граней] = { x: [], y: [] }; }
    г.глубина = глубина;
    г.свой = рисовать;
    _граней++;
  }

  function призма(cx, cy0, cz, нx, нz, вx, вz, высота, мат) {
    var y0 = cy0, y1 = cy0 + высота;
    var н = [{ x: cx - нx, z: cz - нz }, { x: cx + нx, z: cz - нz },
             { x: cx + нx, z: cz + нz }, { x: cx - нx, z: cz + нz }];
    var в = [{ x: cx - вx, z: cz - вz }, { x: cx + вx, z: cz - вz },
             { x: cx + вx, z: cz + вz }, { x: cx - вx, z: cz + вz }];
    var т = function (p, y) { return { x: p.x, y: y, z: p.z }; };

    var наклон = [
      { i: 0, j: 1, н: { x: 0, y: (нz - вz) / высота, z: -1 } },
      { i: 1, j: 2, н: { x: 1, y: (нx - вx) / высота, z: 0 } },
      { i: 2, j: 3, н: { x: 0, y: (нz - вz) / высота, z: 1 } },
      { i: 3, j: 0, н: { x: -1, y: (нx - вx) / высота, z: 0 } }
    ];
    наклон.forEach(function (г) {
      грань([т(н[г.i], y0), т(н[г.j], y0), т(в[г.j], y1), т(в[г.i], y1)],
            мат, г.н);
    });
    грань([т(в[0], y1), т(в[1], y1), т(в[2], y1), т(в[3], y1)], мат,
          { x: 0, y: 1, z: 0 });
    грань([т(н[0], y0), т(н[3], y0), т(н[2], y0), т(н[1], y0)], мат,
          { x: 0, y: -1, z: 0 });
  }

  function коробка(cx, cy, cz, пx, пy, пz, мат) {
    призма(cx, cy - пy, cz, пx, пz, пx, пz, пy * 2, мат);
  }

  function вальма(cx, cy, cz, пx, пz, высота, мат) {
    var кx = пx * 0.42;
    var н = [{ x: cx - пx, z: cz - пz }, { x: cx + пx, z: cz - пz },
             { x: cx + пx, z: cz + пz }, { x: cx - пx, z: cz + пz }];
    var к0 = { x: cx - кx, y: cy + высота, z: cz };
    var к1 = { x: cx + кx, y: cy + высота, z: cz };
    var т = function (p) { return { x: p.x, y: cy, z: p.z }; };
    var с = Math.sqrt(пz * пz + высота * высота) || 1;
    грань([т(н[0]), т(н[1]), к1, к0], мат, { x: 0, y: пz / с, z: -высота / с });
    грань([т(н[3]), т(н[2]), к1, к0], мат, { x: 0, y: пz / с, z: высота / с });
    var с2 = Math.sqrt((пx - кx) * (пx - кx) + высота * высота) || 1;
    грань([т(н[1]), т(н[2]), к1], мат, { x: высота / с2, y: (пx - кx) / с2, z: 0 });
    грань([т(н[0]), т(н[3]), к0], мат, { x: -высота / с2, y: (пx - кx) / с2, z: 0 });
  }

  function наЗемлю(x, y, z) {
    var k = y / СВЕТ.y;
    return { x: x - СВЕТ.x * k, z: z - СВЕТ.z * k };
  }

  function оболочка(точки) {
    var т = точки.slice().sort(function (a, b) {
      return a.x - b.x || a.z - b.z;
    });
    function крест(o, a, b) {
      return (a.x - o.x) * (b.z - o.z) - (a.z - o.z) * (b.x - o.x);
    }
    var низ = [], верх = [], i;
    for (i = 0; i < т.length; i++) {
      while (низ.length >= 2 &&
             крест(низ[низ.length - 2], низ[низ.length - 1], т[i]) <= 0) низ.pop();
      низ.push(т[i]);
    }
    for (i = т.length - 1; i >= 0; i--) {
      while (верх.length >= 2 &&
             крест(верх[верх.length - 2], верх[верх.length - 1], т[i]) <= 0) верх.pop();
      верх.push(т[i]);
    }
    низ.pop(); верх.pop();
    return низ.concat(верх);
  }

  function тень(габариты, сила) {

    var на = габариты.map(function (т) { return наЗемлю(т.x, т.y, т.z); });
    var о = оболочка(на);
    if (о.length < 3) return;
    var высота = 0;
    габариты.forEach(function (т) { высота = Math.max(высота, т.y); });

    ТЕНИ.push({ точки: о, сила: сила * П.силаТени,
                размытие: Math.min(6, 1.6 + высота * 0.35) });
  }

  function габаритКоробки(cx, cy0, cz, пx, пz, высота) {
    var р = [];
    [-1, 1].forEach(function (знакX) {
      [-1, 1].forEach(function (знакZ) {
        р.push({ x: cx + знакX * пx, y: cy0, z: cz + знакZ * пz });
        р.push({ x: cx + знакX * пx, y: cy0 + высота, z: cz + знакZ * пz });
      });
    });
    return р;
  }

  function подстанция() {
    var ш = ТП.ш * 0.5, г = ТП.г * 0.46;
    тень(габаритКоробки(ТП.x, 0, ТП.z, ш * 1.12, г * 1.12, ТП.в + 1.2), 1.0);

    призма(ТП.x, 0, ТП.z, ш * 1.10, г * 1.10, ш * 1.06, г * 1.06, 0.34, П.цоколь);
    призма(ТП.x, 0.34, ТП.z, ш, г, ш, г, ТП.в, П.корпус);
    var zф = ТП.z - г - 0.015;

    грань([{ x: ТП.x - 0.85, y: 0.40, z: zф }, { x: ТП.x + 0.85, y: 0.40, z: zф },
           { x: ТП.x + 0.85, y: 2.55, z: zф }, { x: ТП.x - 0.85, y: 2.55, z: zф }],
          П.дверь, { x: 0, y: 0, z: -1 });
    грань([{ x: ТП.x - 0.62, y: 0.55, z: zф - 0.01 },
           { x: ТП.x + 0.62, y: 0.55, z: zф - 0.01 },
           { x: ТП.x + 0.62, y: 2.40, z: zф - 0.01 },
           { x: ТП.x - 0.62, y: 2.40, z: zф - 0.01 }],
          { цвет: смешать(П.дверь.цвет, [255, 255, 255], 0.10), блеск: 0.18 },
          { x: 0, y: 0, z: -1 });

    for (var i = 0; i < 3; i++) {
      var y = 2.95 + i * 0.26;
      грань([{ x: ТП.x - 1.05, y: y, z: zф }, { x: ТП.x + 1.05, y: y, z: zф },
             { x: ТП.x + 1.05, y: y + 0.14, z: zф },
             { x: ТП.x - 1.05, y: y + 0.14, z: zф }],
            П.металл, { x: 0, y: 0.35, z: -1 });
    }

    призма(ТП.x, ТП.в + 0.34, ТП.z, ш * 1.14, г * 1.16, ш * 1.06, г * 1.08,
           0.30, П.кровляТП);

    [-1, 1].forEach(function (с) {
      коробка(ТП.x + с * 1.5, ТП.в + 0.90, ТП.z, 0.09, 0.28, 0.09, П.металл);
      for (var k = 0; k < 3; k++) {
        призма(ТП.x + с * 1.5 - (0.22 - k * 0.04), ТП.в + 1.02 + k * 0.13,
               ТП.z - (0.22 - k * 0.04),
               0.22 - k * 0.04, 0.22 - k * 0.04,
               0.17 - k * 0.04, 0.17 - k * 0.04, 0.11, П.изолятор);
      }
    });
    return zф;
  }

  function стойка(о) {

    var верх = точка(о.x, о.h, о.z), низ = точка(о.x, 0, о.z);
    var пикселей = Math.abs(низ.Y - верх.Y);
    var подробно = пикселей > 62;

    тень(габаритКоробки(о.x, 0, о.z, 0.24, 0.24, о.h), 0.85);

    призма(о.x, 0, о.z, 0.22, 0.22, 0.14, 0.14, о.h, П.бетон);

    коробка(о.x, о.h - 0.55, о.z, 0.07, 0.06, 1.45, П.металл);
    коробка(о.x, о.h - 1.35, о.z, 0.06, 0.05, 1.05, П.металл);
    if (!подробно) return;
    [-1, 1].forEach(function (с) {

      грань([{ x: о.x - 0.045, y: о.h - 0.64, z: о.z + с * 1.3 },
             { x: о.x + 0.045, y: о.h - 0.64, z: о.z + с * 1.3 },
             { x: о.x + 0.045, y: о.h - 1.55, z: о.z + с * 0.14 },
             { x: о.x - 0.045, y: о.h - 1.55, z: о.z + с * 0.14 }],
            П.металл, { x: 0, y: 0.42, z: с * 0.9 });
      коробка(о.x, о.h - 0.34, о.z + с * 1.35, 0.10, 0.16, 0.10, П.изолятор);
      коробка(о.x, о.h - 1.14, о.z + с * 0.95, 0.085, 0.13, 0.085, П.изолятор);
    });
  }

  function дом(д) {
    var пx = д.ш * 0.5, пz = д.г * 0.5;
    тень(габаритКоробки(д.x, 0, д.z, пx * 1.12, пz * 1.12, д.в + 1.5), 0.95);
    призма(д.x, 0, д.z, пx * 1.04, пz * 1.04, пx * 1.04, пz * 1.04, 0.18,
           П.цоколь);
    призма(д.x, 0.18, д.z, пx, пz, пx, пz, д.в, П.стена);
    вальма(д.x, д.в + 0.18, д.z, пx * 1.12, пz * 1.12, 1.35, П.кровля);
    var zф = д.z - пz - 0.012;
    [[-1.15, -0.45], [0.45, 1.15]].forEach(function (о) {
      грань([{ x: д.x + о[0], y: 1.05, z: zф }, { x: д.x + о[1], y: 1.05, z: zф },
             { x: д.x + о[1], y: 1.95, z: zф }, { x: д.x + о[0], y: 1.95, z: zф }],
            П.окно, { x: 0, y: 0, z: -1 });
    });
    грань([{ x: д.x - 0.30, y: 0.18, z: zф }, { x: д.x + 0.30, y: 0.18, z: zф },
           { x: д.x + 0.30, y: 1.72, z: zф }, { x: д.x - 0.30, y: 1.72, z: zф }],
          П.дверь, { x: 0, y: 0, z: -1 });

    призма(д.x + пx * 0.52, д.в + 0.7, д.z + пz * 0.30, 0.16, 0.16,
           0.15, 0.15, 1.05, П.кровляТП);

    коробка(д.x, д.в + 0.55, д.z - пz, 0.06, 0.20, 0.06, П.металл);
  }

  function провод(п, сек, номер) {

    var шагов = 18, точки = [], провис = п.ввод ? 0.28 : 1.0;
    for (var i = 0; i <= шагов; i++) {
      var t = i / шагов;
      точки.push({
        x: п.a.x + (п.b.x - п.a.x) * t,
        y: п.a.y + (п.b.y - п.a.y) * t - провис * Math.sin(Math.PI * t),
        z: п.a.z + (п.b.z - п.a.z) * t
      });
    }
    var проекции = точки.map(function (т) { return точка(т.x, т.y, т.z); });
    var глубина = (проекции[0].глубина + проекции[шагов].глубина) / 2;
    var д = Math.max(0, Math.min(1, (глубина - 96) / 150));
    var тонП = смешать(П.провод, П.горизонт, д * 0.6);
    var тонИ = смешать(П.импульс, П.горизонт, д * 0.45);

    var фаза = (тише || !п.импульс) ? -1
      : (((сек * 0.34 - (п.уровень || 0) * 0.17 + номер * 0.004) % 1) + 1) % 1;
    своё(глубина, function () {
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.strokeStyle = цвет(тонП, п.ввод ? 0.42 : 0.62);
        ctx.lineWidth = (п.ввод ? 0.9 : 1.35) * Math.max(0.55, проекции[0].f * 0.09);
        ctx.beginPath();
        ctx.moveTo(проекции[0].X, проекции[0].Y);
        for (var j = 1; j <= шагов; j++)
          ctx.lineTo(проекции[j].X, проекции[j].Y);
        ctx.stroke();
        if (фаза < 0 || фаза > 0.999) return;

        var центр = фаза * шагов;
        for (var k = 0; k < 6; k++) {
          var a = центр - k * 0.9, b = a - 0.9;
          if (b < 0) break;
          var pa = проекции[Math.max(0, Math.min(шагов, Math.round(a)))];
          var pb = проекции[Math.max(0, Math.min(шагов, Math.round(b)))];
          ctx.strokeStyle = цвет(тонИ, 0.46 * (1 - k / 6));
          ctx.lineWidth = (п.ввод ? 1.1 : 1.6) *
                          Math.max(0.6, pa.f * 0.09) * (1 - k / 8);
          ctx.beginPath();
          ctx.moveTo(pa.X, pa.Y);
          ctx.lineTo(pb.X, pb.Y);
          ctx.stroke();
        }

        var p = проекции[Math.max(0, Math.min(шагов, Math.round(центр)))];
        var r = Math.max(1.0, 1.5 * p.f * 0.09);
        var сияние = ctx.createRadialGradient(p.X, p.Y, 0, p.X, p.Y, r * 2.6);
        сияние.addColorStop(0, цвет(тонИ, 0.26));
        сияние.addColorStop(1, цвет(тонИ, 0));
        ctx.fillStyle = сияние;
        ctx.beginPath();
        ctx.arc(p.X, p.Y, r * 2.6, 0, 6.284);
        ctx.fill();
        ctx.fillStyle = цвет(смешать(тонИ, [255, 255, 255], 0.25), 0.95);
        ctx.beginPath();
        ctx.arc(p.X, p.Y, r, 0, 6.284);
        ctx.fill();
    });
  }

  function земля(w, h) {

    var шаг = 10, предел = Math.ceil(РАДИУС / шаг) * шаг;
    ctx.lineWidth = 1;
    линииЗемли(предел, шаг);

    var ц = точка(0, 0, 0);
    var r = РАДИУС * ц.f * 1.35;
    var п = ctx.createRadialGradient(ц.X, ц.Y, 0, ц.X, ц.Y, r);
    var с0 = П.тьма ? 0.16 : 0.045;
    [0, 0.25, 0.5, 0.7, 0.85, 1].forEach(function (t) {
      п.addColorStop(t, цвет(П.земля, с0 * Math.pow(1 - t, 1.8)));
    });
    ctx.fillStyle = п;
    ctx.beginPath();
    ctx.ellipse(ц.X, ц.Y, r, r * 0.5, 0, 0, 6.284);
    ctx.fill();
  }

  var СТУПЕНЕЙ = 5;
  var _ст_x = [], _ст_n = [];
  (function () {
    for (var i = 0; i < СТУПЕНЕЙ; i++) {
      _ст_x[i] = new Float64Array(4096);
      _ст_n[i] = 0;
    }
  })();

  function линииЗемли(предел, шаг) {
    var i, к, N = 8;
    for (i = 0; i < СТУПЕНЕЙ; i++) _ст_n[i] = 0;

    function отрезок(x1, z1, x2, z2) {
      for (var j = 0; j < N; j++) {
        var t0 = j / N, t1 = (j + 1) / N;
        var ax = x1 + (x2 - x1) * t0, az = z1 + (z2 - z1) * t0;
        var bx = x1 + (x2 - x1) * t1, bz = z1 + (z2 - z1) * t1;
        var dx = (ax + bx) / 2, dz = (az + bz) / 2;
        var сила = 1 - Math.min(1, Math.sqrt(dx * dx + dz * dz) / РАДИУС);
        if (сила <= 0.06) continue;
        var ст = Math.min(СТУПЕНЕЙ - 1, (сила * сила * СТУПЕНЕЙ) | 0);
        var м = _ст_x[ст], н = _ст_n[ст];
        if (н + 4 > м.length) continue;
        var p1 = точка(ax, 0, az), p2 = точка(bx, 0, bz);
        м[н] = p1.X; м[н + 1] = p1.Y; м[н + 2] = p2.X; м[н + 3] = p2.Y;
        _ст_n[ст] = н + 4;
      }
    }
    for (к = -предел; к <= предел; к += шаг) {
      отрезок(к, -предел, к, предел);
      отрезок(-предел, к, предел, к);
    }
    var основа = П.тьма ? 0.22 : 0.17;
    for (i = 0; i < СТУПЕНЕЙ; i++) {
      var н2 = _ст_n[i];
      if (!н2) continue;
      var м2 = _ст_x[i];
      ctx.strokeStyle = цвет(П.сетка, основа * ((i + 1) / СТУПЕНЕЙ));
      ctx.beginPath();
      for (var k = 0; k < н2; k += 4) {
        ctx.moveTo(м2[k], м2[k + 1]);
        ctx.lineTo(м2[k + 2], м2[k + 3]);
      }
      ctx.stroke();
    }
  }

  var _полотноТеней = null;
  function полотноТеней(w, h) {
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    if (!_полотноТеней) _полотноТеней = document.createElement("canvas");
    var нw = Math.round(w * dpr), нh = Math.round(h * dpr);
    if (_полотноТеней.width !== нw || _полотноТеней.height !== нh) {
      _полотноТеней.width = нw;
      _полотноТеней.height = нh;
    }
    return _полотноТеней;
  }

  var t0 = 0;

  var СДВИГ = null;

  var прежний = window.voltplanSceneSeek;
  window.voltplanSceneSeek = function (с) {
    СДВИГ = (с === null || с === undefined) ? null : +с;
    if (typeof прежний === "function") прежний(с);
  };

  function кадр(время) {
    var w = ХОЛСТ.clientWidth, h = ХОЛСТ.clientHeight;
    if (!w || !h) return;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    if (ХОЛСТ.width !== Math.round(w * dpr)) {
      ХОЛСТ.width = Math.round(w * dpr);
      ХОЛСТ.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (!t0) t0 = время;
    var сек = СДВИГ === null ? (время - t0) / 1000 : СДВИГ;

    целX += (мышьX - целX) * 0.06;
    целY += (мышьY - целY) * 0.06;

    угол = тише ? УГОЛ0 : УГОЛ0 + сек * 0.058;
    обновитьКамеру();
    подогнать(w, h);

    _граней = 0;
    ТЕНИ.length = 0;

    земля(w, h);

    var zф = подстанция();
    ОПОРЫ.forEach(стойка);
    ДОМА.forEach(дом);

    if (ТЕНИ.length) {
      var пт = полотноТеней(w, h);
      var к = пт.getContext("2d");
      к.setTransform(1, 0, 0, 1, 0, 0);
      к.clearRect(0, 0, пт.width, пт.height);
      к.setTransform(dpr, 0, 0, dpr, 0, 0);
      к.fillStyle = цвет(П.тень, 1);
      for (var т_и = 0; т_и < ТЕНИ.length; т_и++) {
        var т = ТЕНИ[т_и];
        к.globalAlpha = т.сила;
        к.beginPath();
        var p0 = точка(т.точки[0].x, 0, т.точки[0].z);
        к.moveTo(p0.X, p0.Y);
        for (var j = 1; j < т.точки.length; j++) {
          var p = точка(т.точки[j].x, 0, т.точки[j].z);
          к.lineTo(p.X, p.Y);
        }
        к.closePath();
        к.fill();
      }
      к.globalAlpha = 1;
      ctx.save();
      ctx.filter = "blur(3px)";
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(пт, 0, 0);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.restore();
    }

    ПРОВОДА.forEach(function (п, i) { провод(п, сек, i); });

    var список = ГРАНИ.slice(0, _граней);
    список.sort(function (a, b) { return b.глубина - a.глубина; });
    for (var i = 0; i < список.length; i++) {
      var г = список[i];
      if (г.свой) { г.свой(); continue; }
      ctx.beginPath();
      ctx.moveTo(г.x[0], г.y[0]);
      for (var k = 1; k < г.n; k++) ctx.lineTo(г.x[k], г.y[k]);
      ctx.closePath();
      ctx.fillStyle = г.заливка;
      ctx.fill();

      var мнx = г.x[0], мкx = г.x[0], мнy = г.y[0], мкy = г.y[0];
      for (k = 1; k < г.n; k++) {
        if (г.x[k] < мнx) мнx = г.x[k]; else if (г.x[k] > мкx) мкx = г.x[k];
        if (г.y[k] < мнy) мнy = г.y[k]; else if (г.y[k] > мкy) мкy = г.y[k];
      }
      if (мкx - мнx > 7 || мкy - мнy > 7) {
        ctx.strokeStyle = г.кромка;
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }
    }

    подписьТП(zф);
  }

  function подписьТП(zф) {

    var м = точка(ТП.x, ТП.в + 4.6, zф);
    var к = Math.max(0.72, Math.min(1.25, м.f * 0.11));
    var текст = ({ en: "TS 10/0.4 kV", zh: "变电站 10/0.4 kV" })[язык()] || "ТП 10/0,4 кВ";
    ctx.font = "700 " + (10.5 * к).toFixed(1) + "px " +
               '"JetBrains Mono","Cascadia Code",ui-monospace,Consolas,monospace';
    var ш = ctx.measureText(текст).width + 15 * к, в = 19 * к;
    var x = м.X - ш / 2, y = м.Y - в - 8 * к;
    ctx.beginPath();
    var r = в / 2;
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + ш, y, x + ш, y + в, r);
    ctx.arcTo(x + ш, y + в, x, y + в, r);
    ctx.arcTo(x, y + в, x, y, r);
    ctx.arcTo(x, y, x + ш, y, r);
    ctx.closePath();
    ctx.fillStyle = П.тьма ? "rgba(15,24,41,.86)" : "rgba(255,255,255,.90)";
    ctx.fill();
    ctx.strokeStyle = цвет(П.подпись, 0.30);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = цвет(П.подпись, 1);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(текст, м.X, y + в / 2 + 0.5);

    ctx.strokeStyle = цвет(П.подпись, 0.28);
    ctx.beginPath();
    ctx.moveTo(м.X, y + в);
    ctx.lineTo(м.X, м.Y - 1);
    ctx.stroke();
  }

  var идёт = false, кадрId = 0;

  var ПРЕДЕЛ_ЧАСТОТЫ = 1000 / 32;
  var _последний = 0;

  function цикл(время) {
    if (время - _последний >= ПРЕДЕЛ_ЧАСТОТЫ) {
      _последний = время;
      кадр(время);
    }
    if (идёт) кадрId = requestAnimationFrame(цикл);
  }
  function пуск() {
    if (идёт) return;
    идёт = true;
    кадрId = requestAnimationFrame(цикл);
  }
  function стоп() {
    идёт = false;
    if (кадрId) cancelAnimationFrame(кадрId);
  }

  var поле = ХОЛСТ.parentElement || ХОЛСТ;
  поле.addEventListener("pointermove", function (e) {
    var r = ХОЛСТ.getBoundingClientRect();
    мышьX = ((e.clientX - r.left) / r.width - 0.5) * 2;
    мышьY = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  поле.addEventListener("pointerleave", function () { мышьX = 0; мышьY = 0; });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (записи) {
      записи.forEach(function (з) { з.isIntersecting ? пуск() : стоп(); });
    }, { threshold: 0.05 }).observe(ХОЛСТ);
  } else {
    пуск();
  }
  document.addEventListener("visibilitychange", function () {
    document.hidden ? стоп() : пуск();
  });
  requestAnimationFrame(кадр);
})();
