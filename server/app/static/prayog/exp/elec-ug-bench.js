/* Prayogshala studio rig `elec-ug-bench`: ONE electronics bench - a solderless breadboard, a variable DC bench
   supply, a small low-voltage source and two 4.5-digit digital multimeters - serving every undergraduate DC
   electronics set-up in app/prayog/labs/elec_ug.py. The circuit on the board changes with the lab; the apparatus,
   the hand actions and the procedure do not.
   Physics: the lab's own kernel from kernels.js (fet / opamp / zenreg / solar from packs/elec_ug.js, transistor from
   packs/elec11.js) on the lab's own params - the same numbers the server checks. Nothing here invents a reading. */
HoolaStudio.define('elec-ug-bench', function (S) {
  var T = S.T, M = S.M, HK = window.HoolaKernels, assign = HK.assign;
  var KK = HK.K[S.lab.kernel], p = HK.paramsFor(S.lab.kernel, S.lab.params);
  var BASE = (S.lab.variant && S.lab.variant.base) || S.lab.id;
  var SAMPLE = (S.lab.variant && S.lab.variant.sample) || '';

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function round(v, d) { var k = Math.pow(10, d); return Math.round(v * k) / k; }
  function fmt(v, d) { return (isFinite(v) ? v : 0).toFixed(d); }
  function wpos(o, x, y, z) { o.updateMatrixWorld(true); return o.localToWorld(new T.Vector3(x || 0, y || 0, z || 0)); }
  function arr(v) { return [v.x, v.y, v.z]; }
  function ohm(r) {
    r = +r;
    if (!isFinite(r)) return '—';
    return r >= 1000 ? String(+(r / 1000).toFixed(r >= 10000 ? 0 : 1)) + ' kΩ' : String(+r.toFixed(r < 10 ? 1 : 0)) + ' Ω';
  }
  function slope(pts) {
    var n = pts.length, sx = 0, sy = 0, sxy = 0, sxx = 0, i, den;
    if (n < 2) return 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; sxy += pts[i][0] * pts[i][1]; sxx += pts[i][0] * pts[i][0]; }
    den = n * sxx - sx * sx;
    return den === 0 ? 0 : (n * sxy - sx * sy) / den;
  }
  function geom(lo, hi, n) { var out = [], i; for (i = 0; i < n; i++) out.push(round(lo * Math.pow(hi / lo, i / (n - 1)), 4)); return out; }
  function span(lo, hi, st) { var out = [], v; for (v = lo; v <= hi + 1e-9; v += st) out.push(round(v, 4)); return out; }

  // the live readings of this circuit for a set of overrides: always through the lab's own kernel
  function readAt(over) { var q = assign(p, over || {}); return KK.view(KK.init(q, null), q, null); }

  // =============================================================================================== the lab's plan
  // Each set-up names its components, the controls the hand turns, what the two meters read, what goes in the
  // record book and how the result is worked out. Everything else on this bench is shared.
  var PLANS = {};

  PLANS['bjt-ce-current-gain'] = function () { return {
    comp: 'to92', compName: SAMPLE || 'n-p-n transistor (TO-92)',
    parts: [{ r: p.Rb, tag: 'R_B' }, { r: p.Rc, tag: 'R_C' }],
    wiring: 'Base supply → R_B (' + ohm(p.Rb) + ') → base.  Collector supply ' + fmt(p.Vcc, 1) +
      ' V → R_C (' + ohm(p.Rc) + ') → collector.  Emitter → common negative rail.',
    controls: [{ param: 'Vbb', label: 'Base supply V_BB', unit: 'V', digits: 2, vmax: 5,
      vals: span(0.8, 3.2, 0.3), knob: 'aux' }],
    m1: { fn: 'DC µA', label: 'Base current I_B', unit: 'µA', digits: 2, lc: 0.01, get: function (v) { return v.I_b * 1e6; } },
    m2: { fn: 'DC mA', label: 'Collector current I_C', unit: 'mA', digits: 3, lc: 0.001, get: function (v) { return v.I_c * 1000; } },
    extra: [{ key: 'Vbe', label: 'V_BE (V)', digits: 3, get: function (v) { return v.V_be; } },
      { key: 'Vce', label: 'V_CE (V)', digits: 2, get: function (v) { return v.V_ce; } }],
    cols: [{ label: 'V_BB (V)', key: 'set', digits: 2 }, { label: 'I_B (µA)', key: 'm1', digits: 2 },
      { label: 'I_C (mA)', key: 'm2', digits: 3 }, { label: 'V_BE (V)', key: 'Vbe', digits: 3 },
      { label: 'V_CE (V)', key: 'Vce', digits: 2 }],
    need: 7,
    graph: { x: function (r) { return r.m1; }, y: function (r) { return r.m2; }, xlabel: 'I_B (µA)', ylabel: 'I_C (mA)' },
    result: function (rows) {
      var pts = rows.map(function (r) { return [r.m1 * 1e-6, r.m2 * 1e-3]; });
      var mid = rows.map(function (r) { return r.set; }).sort(function (a, b) { return a - b; });
      var c = mid[Math.floor(mid.length / 2)], d = 0.02;
      var a = readAt({ Vbb: c - d }), b = readAt({ Vbb: c + d });
      return { label: 'Current gain β = ΔI_C / ΔI_B', value: slope(pts), unit: '', digits: 1,
        truth: (b.I_c - a.I_c) / (b.I_b - a.I_b),
        note: 'Slope of the I_C against I_B line; the true value is the kernel\'s own ΔI_C/ΔI_B at V_BB = ' + fmt(c, 2) + ' V.' };
    },
    resultNote: 'β is a pure number, a few hundred for a small-signal transistor. It is not a constant of nature: ' +
      'it changes with the collector current, the temperature and from one specimen to the next, which is why a ' +
      'well-designed amplifier is biased so that its working point hardly depends on β.',
    chips: ['Why does V_BE hardly move?', 'What is the current gain here?', 'Why keep V_CE high?', 'Check my readings'],
    viva: [['In common emitter, which current is the input?', ['The base current', 'The collector current', 'The emitter current'], 0,
      'The base current is the input and the collector current the output; their ratio is β.'],
      ['Why is R_B needed in the base lead?', ['The base-emitter diode would take a destructive current without it',
        'It sets the collector voltage', 'It stops oscillation'], 0,
        'A forward-biased junction has almost no resistance of its own.']],
  }; };

  function fetPlan(isMos) {
    var unk = isMos ? p.Vth : p.Vp;
    var lo = isMos ? unk + 0.2 : 0, hi = isMos ? unk + 1.4 : -0.6 * Math.abs(unk);
    var st = (hi - lo) / 9;
    return {
      comp: 'to92', compName: SAMPLE || (isMos ? 'n-channel enhancement MOSFET' : 'n-channel JFET'),
      parts: [{ r: p.Rd, tag: 'R_D' }],
      wiring: 'Gate ← low-voltage source.  Drain → R_D (' + ohm(p.Rd) + ') → ' + fmt(p.Vdd, 1) +
        ' V drain supply.  Source → common negative rail.',
      controls: [{ param: 'Vgs', label: 'Gate-source voltage V_GS', unit: 'V', digits: 2,
        vmax: isMos ? 6 : -10, vals: span(Math.min(lo, hi), Math.max(lo, hi), Math.abs(st)), knob: 'aux' }],
      m1: { fn: 'DC V', label: 'Gate-source voltage', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_gs; } },
      m2: { fn: 'DC mA', label: 'Drain current I_D', unit: 'mA', digits: 2, lc: 0.01, get: function (v) { return v.I_d * 1000; } },
      extra: [{ key: 'Vds', label: 'V_DS (V)', digits: 2, get: function (v) { return v.V_ds; } }],
      cols: [{ label: 'V_GS (V)', key: 'm1', digits: 3 }, { label: 'I_D (mA)', key: 'm2', digits: 2 },
        { label: '√I_D (√mA)', key: 'sq', digits: 3 }, { label: 'V_DS (V)', key: 'Vds', digits: 2 }],
      derive: function (row) { row.sq = Math.sqrt(Math.max(row.m2, 0)); },
      need: 7,
      graph: { x: function (r) { return r.m1; }, y: function (r) { return r.sq; }, xlabel: 'V_GS (V)', ylabel: '√I_D (√mA)' },
      result: function (rows) {
        var pts = rows.map(function (r) { return [r.m1, Math.sqrt(Math.max(r.m2, 0) / 1000)]; });
        var m = slope(pts), n = pts.length, mx = 0, my = 0, i;
        for (i = 0; i < n; i++) { mx += pts[i][0]; my += pts[i][1]; }
        mx /= n; my /= n;
        return { label: isMos ? 'Threshold voltage V_th' : 'Pinch-off voltage V_P',
          value: m === 0 ? NaN : mx - my / m, unit: 'V', digits: 3, truth: unk,
          note: 'Where the straight line through √I_D against V_GS cuts the voltage axis.' };
      },
      resultNote: isMos
        ? 'Below the threshold there is no channel at all, so the current is only leakage. Past it the square law ' +
          'takes over, and the straight line through √I_D points straight back at V_th.'
        : 'The pinch-off voltage is where the gate has squeezed the channel shut. Reading it as the intercept of ' +
          'the √I_D line is far more reliable than hunting for the gate voltage at which the meter finally reads zero.',
      chips: isMos ? ['What is the threshold voltage?', 'Why no current at low V_GS?', 'Why is √I_D a straight line?', 'Check my readings']
        : ['What is the pinch-off voltage?', 'Why does the gate take no current?', 'Why is √I_D a straight line?', 'Check my readings'],
      viva: [[isMos ? 'An enhancement MOSFET with its gate at zero is' : 'A JFET with its gate at zero carries',
        isMos ? ['off: there is no channel', 'fully on', 'damaged'] : ['its largest drain current, I_DSS', 'no current', 'a reverse current'], 0,
        isMos ? 'The gate has to build the channel before anything flows.' : 'The channel is widest with no gate voltage squeezing it.'],
        ['Why is the drain resistor kept small in this experiment?',
          ['So the device stays in saturation across the whole sweep', 'To protect the meter', 'To raise the gain'], 0,
          'A large R_D would drag the drain below the knee and the square law would no longer hold.']],
    };
  }
  PLANS['jfet-transfer-characteristic'] = function () { return fetPlan(false); };
  PLANS['mosfet-transfer-characteristic'] = function () { return fetPlan(true); };

  PLANS['zener-shunt-regulator'] = function () {
    // start the sweep where the diode really is in breakdown: the input at which it carries 8 mA
    var lo = (function () { var a = p.Vz, b = p.Vz + 40, i, mid;
      for (i = 0; i < 60; i++) { mid = (a + b) / 2; if (readAt({ Vin: mid }).I_z < 0.008) a = mid; else b = mid; }
      return Math.ceil(b * 2) / 2; })();
    return {
      comp: 'zener', compName: SAMPLE || 'Zener diode ' + fmt(p.Vz, 1) + ' V',
      parts: [{ r: p.Rs, tag: 'R_S' }, { r: p.RL, tag: 'R_L' }],
      wiring: 'Supply → R_S (' + ohm(p.Rs) + ') → Zener cathode (banded end).  Zener anode → common negative rail.  ' +
        'Load R_L (' + ohm(p.RL) + ') across the Zener.',
      controls: [{ param: 'Vin', label: 'Input voltage V_in', unit: 'V', digits: 1, vmax: 30,
        vals: span(lo, lo + 6, 1), knob: 'main' }],
      m1: { fn: 'DC V', label: 'Input voltage', unit: 'V', digits: 2, lc: 0.01, get: function (v, q) { return q.Vin; } },
      m2: { fn: 'DC V', label: 'Output voltage across the load', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_o; } },
      extra: [{ key: 'Iz', label: 'I_Z (mA)', digits: 2, get: function (v) { return v.I_z * 1000; } },
        { key: 'IL', label: 'I_L (mA)', digits: 2, get: function (v) { return v.I_L * 1000; } }],
      cols: [{ label: 'V_in (V)', key: 'm1', digits: 2 }, { label: 'V_out (V)', key: 'm2', digits: 3 },
        { label: 'I_Z (mA)', key: 'Iz', digits: 2 }, { label: 'I_L (mA)', key: 'IL', digits: 2 }],
      need: 6,
      graph: { x: function (r) { return r.m1; }, y: function (r) { return r.m2; }, xlabel: 'V_in (V)', ylabel: 'V_out (V)' },
      result: function (rows) {
        var q = rows.slice().sort(function (a, b) { return a.set - b.set; });
        var a = q[0], b = q[q.length - 1], dv = b.set - a.set;
        if (!dv) return null;
        var ta = readAt({ Vin: a.set }).V_o, tb = readAt({ Vin: b.set }).V_o;
        return { label: 'Line regulation ΔV_out / ΔV_in', value: 1000 * (b.m2 - a.m2) / dv, unit: 'mV/V', digits: 2,
          truth: 1000 * (tb - ta) / dv,
          note: 'From the two ends of your table, ' + fmt(a.set, 1) + ' V to ' + fmt(b.set, 1) + ' V in.' };
      },
      resultNote: 'A few tens of millivolts of output for a whole volt of input: that is what a shunt regulator ' +
        'buys for the price of one resistor and one diode. The limit is the diode\'s dynamic resistance r_z, ' +
        'which also sets how well the output holds up when the load changes.',
      chips: ['Why does the output hardly move?', 'What is the Zener current here?', 'What happens if the load grows?', 'Check my readings'],
      viva: [['The output of this regulator is held steady by', ['the small dynamic resistance of the Zener in breakdown',
        'the load resistor', 'the series resistor alone'], 0,
        'r_z is a few ohms, so the input change divides almost entirely across R_S.'],
        ['Taking the input below the start of your sweep would', ['take the diode out of breakdown and the output would follow the input',
          'raise the output', 'damage the load'], 0, 'With no Zener current there is no regulation left.']],
    };
  };

  PLANS['solar-cell-characteristic'] = function () { return {
    comp: 'solar', compName: SAMPLE || 'Silicon solar cell',
    parts: [],
    wiring: 'Cell (+) → ammeter → load potentiometer → cell (−).  Voltmeter across the cell.  Lamp fixed above it.',
    controls: [{ param: 'RL', label: 'Load resistance', unit: 'Ω', digits: 2, vmax: 0,
      vals: (function () { var m = KK.measure(p), rm = m.V_m / m.I_m;
        return geom(0.1, rm * 0.55, 5).concat(span(round(rm * 0.6, 2), round(rm * 1.5, 2), round(rm * 0.1, 2)))
          .concat(geom(rm * 1.8, 20000, 7)); })(), knob: 'pot' }],
    m1: { fn: 'DC V', label: 'Cell voltage', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_o; } },
    m2: { fn: 'DC mA', label: 'Cell current', unit: 'mA', digits: 2, lc: 0.01, get: function (v) { return v.I_o * 1000; } },
    extra: [],
    cols: [{ label: 'R_L (Ω)', key: 'set', digits: 2 }, { label: 'V (V)', key: 'm1', digits: 3 },
      { label: 'I (mA)', key: 'm2', digits: 2 }, { label: 'P = VI (mW)', key: 'pw', digits: 3 }],
    derive: function (row) { row.pw = row.m1 * row.m2; },
    need: 12,
    graph: { x: function (r) { return r.m1; }, y: function (r) { return r.m2; }, xlabel: 'V (V)', ylabel: 'I (mA)' },
    result: function (rows) {
      var isc = 0, voc = 0, pm = 0, i;
      for (i = 0; i < rows.length; i++) {
        if (rows[i].m2 > isc) isc = rows[i].m2;
        if (rows[i].m1 > voc) voc = rows[i].m1;
        pm = Math.max(pm, rows[i].m1 * rows[i].m2);
      }
      if (!(isc * voc > 0)) return null;
      return { label: 'Fill factor FF = P_max / (I_sc V_oc)', value: pm / (isc * voc), unit: '', digits: 3,
        truth: KK.measure(p).FF,
        note: 'Largest power in your table ' + fmt(pm, 2) + ' mW, I_sc ' + fmt(isc, 2) + ' mA, V_oc ' + fmt(voc, 3) + ' V.' };
    },
    resultNote: 'The fill factor says how square the I-V curve is. A good crystalline silicon cell reaches about ' +
      '0.7 to 0.8; series resistance in the contacts and leakage at the edges both pull it down, which is why it ' +
      'is the first number a cell maker looks at.',
    chips: ['Where is the maximum power point?', 'Why is no power delivered at open circuit?', 'What does the fill factor mean?', 'Check my readings'],
    viva: [['The open-circuit voltage of a silicon cell is about', ['0.6 V', '1.5 V', '12 V'], 0,
      'It is set by the silicon junction, not by the size of the cell or the light.'],
      ['The maximum power point lies', ['at the knee of the I-V curve', 'at short circuit', 'at open circuit'], 0,
        'Both ends deliver zero power, so the best point is between them.']],
  }; };

  PLANS['opamp-inverting-amplifier'] = function () { return {
    comp: 'dip8', compName: SAMPLE || 'Operational amplifier (8-pin DIL)',
    parts: [{ r: p.R1, tag: 'R_1' }, { r: p.Rf, tag: 'R_f' }],
    wiring: 'Input → R_1 (' + ohm(p.R1) + ') → pin 2 (inverting).  R_f (' + ohm(p.Rf) +
      ') from pin 2 to pin 6 (output).  Pin 3 (non-inverting) to earth.  Supplies ±15 V on pins 7 and 4.',
    // the input range follows the gain, so the output never runs into the rails
    controls: [{ param: 'V1', label: 'Input voltage V_in', unit: 'V', digits: 2, vmax: 5,
      vals: (function () { var vm = round(Math.min(1, 0.6 * p.Vsat * p.R1 / p.Rf), 2), i, out = [];
        for (i = -4; i <= 4; i++) if (i !== 0) out.push(round(vm * i / 4, 3));
        return out; })(), knob: 'aux' }],
    m1: { fn: 'DC V', label: 'Input voltage', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_1; } },
    m2: { fn: 'DC V', label: 'Output voltage', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_o; } },
    extra: [{ key: 'Vn', label: 'V at pin 2 (mV)', digits: 3, get: function (v) { return v.V_n * 1000; } }],
    cols: [{ label: 'V_in (V)', key: 'm1', digits: 3 }, { label: 'V_out (V)', key: 'm2', digits: 3 },
      { label: 'V_out / V_in', key: 'gn', digits: 3 }, { label: 'pin 2 (mV)', key: 'Vn', digits: 3 }],
    derive: function (row) { row.gn = row.m1 === 0 ? 0 : row.m2 / row.m1; },
    need: 6,
    graph: { x: function (r) { return r.m1; }, y: function (r) { return r.m2; }, xlabel: 'V_in (V)', ylabel: 'V_out (V)' },
    result: function (rows) {
      var q = rows.slice().sort(function (a, b) { return a.set - b.set; });
      var a = q[0], b = q[q.length - 1], dv = b.set - a.set;
      if (!dv) return null;
      return { label: 'Voltage gain V_out / V_in', value: slope(rows.map(function (r) { return [r.m1, r.m2]; })),
        unit: '', digits: 3, truth: (readAt({ V1: b.set }).V_o - readAt({ V1: a.set }).V_o) / dv,
        note: 'Slope of the output against the input; −R_f/R_1 is −' + fmt(p.Rf / p.R1, 2) + '.' };
    },
    resultNote: 'The measured gain is the ratio of the two resistors to within a few parts in a hundred thousand, ' +
      'and the inverting input never strays more than a few tens of microvolts from earth. That is negative ' +
      'feedback doing its work: the circuit\'s behaviour belongs to the resistors, not to the amplifier.',
    chips: ['Why is the gain −R_f/R_1?', 'What is a virtual earth?', 'What happens if the input is too large?', 'Check my readings'],
    viva: [['The gain of this amplifier is set by', ['the two resistors', 'the open-loop gain', 'the supply rails'], 0,
      'Feedback hands the gain over to the resistor ratio.'],
      ['The voltage at the inverting input stays near zero because', ['the open-loop gain is enormous',
        'it is wired to earth', 'the input resistor is large'], 0,
        'V_o = A_0(V_p − V_n) with A_0 of a few hundred thousand leaves microvolts across the input.']],
  }; };

  PLANS['opamp-summing-amplifier'] = function () { return {
    comp: 'dip8', compName: SAMPLE || 'Operational amplifier as a summing amplifier',
    parts: [{ r: p.R1, tag: 'R_1' }, { r: p.R2, tag: 'R_2' }, { r: p.R3, tag: 'R_3' }, { r: p.Rf, tag: 'R_f' }],
    wiring: 'Three inputs through equal ' + ohm(p.R1) + ' resistors to pin 2.  R_f (' + ohm(p.Rf) +
      ') from pin 2 to pin 6.  Pin 3 to earth.',
    // each input may go up to a third of what the output can hold, so three of them never reach the rails
    controls: (function () {
      var vm = round(Math.min(2, 0.7 * p.Vsat * p.R1 / p.Rf / 3), 2), i, vs = [];
      for (i = -3; i <= 3; i++) vs.push(round(vm * i / 3, 3));
      return [{ param: 'V1', label: 'First input V_1', unit: 'V', digits: 2, vmax: 5, vals: vs, knob: 'aux' },
        { param: 'V2', label: 'Second input V_2', unit: 'V', digits: 2, vmax: 5, vals: vs, knob: 'aux2' },
        { param: 'V3', label: 'Third input V_3', unit: 'V', digits: 2, vmax: 5, vals: vs, knob: 'aux2' }];
    })(),
    m1: { fn: 'DC V', label: 'Sum of the three inputs', unit: 'V', digits: 3, lc: 0.001,
      get: function (v) { return v.V_1 + v.V_2 + v.V_3; } },
    m2: { fn: 'DC V', label: 'Output voltage', unit: 'V', digits: 3, lc: 0.001, get: function (v) { return v.V_o; } },
    extra: [{ key: 'v1', label: 'V_1 (V)', digits: 2, get: function (v) { return v.V_1; } },
      { key: 'v2', label: 'V_2 (V)', digits: 2, get: function (v) { return v.V_2; } },
      { key: 'v3', label: 'V_3 (V)', digits: 2, get: function (v) { return v.V_3; } }],
    cols: [{ label: 'V_1 (V)', key: 'v1', digits: 2 }, { label: 'V_2 (V)', key: 'v2', digits: 2 },
      { label: 'V_3 (V)', key: 'v3', digits: 2 }, { label: 'ΣV (V)', key: 'm1', digits: 3 },
      { label: 'V_out (V)', key: 'm2', digits: 3 }],
    need: 6,
    graph: { x: function (r) { return r.m1; }, y: function (r) { return r.m2; }, xlabel: 'ΣV (V)', ylabel: 'V_out (V)' },
    result: function (rows) {
      var pts = rows.map(function (r) { return [r.m1, r.m2]; });
      var vm = CTRL[0].vals[CTRL[0].vals.length - 1];
      var lo = { V1: -vm, V2: -vm, V3: -vm }, hi = { V1: vm, V2: vm, V3: vm };
      return { label: 'Gain of the sum, V_out / ΣV', value: slope(pts), unit: '', digits: 3,
        truth: (readAt(hi).V_o - readAt(lo).V_o) / (6 * vm),
        note: 'Slope of the output against the sum of the inputs; −R_f/R is −' + fmt(p.Rf / p.R1, 2) + '.' };
    },
    resultNote: 'The output follows the plain sum of the three inputs, inverted and scaled by R_f/R, no matter how ' +
      'the three are shared out. Each resistor pushes its own current into a node that never moves, so the inputs ' +
      'cannot see one another. Give them resistances 1, 2, 4, 8 and this becomes a digital-to-analogue converter.',
    chips: ['Why do the inputs not interfere?', 'What is the gain of the sum?', 'How would this make a DAC?', 'Check my readings'],
    viva: [['The summing node of this amplifier sits at', ['zero volts, whatever the inputs do', 'the mean of the inputs',
      'the output voltage'], 0, 'It is a virtual earth, held there by the feedback.'],
      ['With equal input resistors the output is', ['−(R_f/R) times the sum of the inputs', 'the largest input',
        'the mean of the inputs'], 0, 'Each input contributes V/R of current and all of it leaves through R_f.']],
  }; };

  var PL = (PLANS[BASE] || PLANS['bjt-ce-current-gain'])();
  var CTRL = PL.controls;

  // =============================================================================================== the bench
  var st = { power: false, checked: false, set: CTRL.map(function (c) { return c.vals[0]; }), idx: CTRL.map(function () { return 0; }) };
  function over() { var o = {}, i; for (i = 0; i < CTRL.length; i++) o[CTRL[i].param] = st.set[i]; return o; }
  function liveQ() { return assign(p, over()); }
  function live() { return st.power ? readAt(over()) : readAt((function () { var o = over(), i; for (i = 0; i < CTRL.length; i++) if (CTRL[i].knob !== 'pot') o[CTRL[i].param] = 0; return o; })()); }
  function meterVal(m) { var v = live(); return round(m.get(v, liveQ()) / m.lc, 0) * m.lc; }

  // ---------- breadboard
  var BW = 0.34, BD = 0.11, BT = 0.011, BZ = -0.03;
  var bbTex = S.canvasTex(1400, 460, function (x, w, h) {
    x.fillStyle = '#efece2'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(0,0,0,.12)'; x.lineWidth = 2; x.strokeRect(6, 6, w - 12, h - 12);
    // power rails
    [[36, '#b8322a', '+'], [h - 36, '#2c5fb4', '−']].forEach(function (rail) {
      x.strokeStyle = rail[1]; x.lineWidth = 3;
      x.beginPath(); x.moveTo(60, rail[0] - 14); x.lineTo(w - 60, rail[0] - 14); x.stroke();
      x.fillStyle = rail[1]; x.font = '700 26px "Public Sans", sans-serif';
      x.fillText(rail[2], 34, rail[0] + 2); x.fillText(rail[2], w - 50, rail[0] + 2);
    });
    // tie-point holes, two banks of five with a central channel
    x.fillStyle = '#7d7668';
    var i, j, y;
    for (i = 0; i < 56; i++) {
      for (j = 0; j < 10; j++) {
        y = 86 + j * 26 + (j >= 5 ? 56 : 0);
        x.fillRect(66 + i * 21, y, 7, 7);
      }
    }
    x.fillStyle = '#d7d2c4'; x.fillRect(50, 86 + 5 * 26 + 6, w - 100, 44);
    x.fillStyle = '#8d8575'; x.font = '600 20px "Public Sans", sans-serif';
    for (i = 0; i < 11; i++) x.fillText(String(i * 5 + 1), 62 + i * 105, 78);
  });
  var bb = S.rounded(BW, BD, BT, 0.004, new T.MeshStandardMaterial({ color: 0xefece2, roughness: 0.6 }));
  bb.rotation.x = -Math.PI / 2; bb.position.set(0, BT / 2, BZ); S.scene.add(bb);
  var bbTop = new T.Mesh(new T.PlaneGeometry(BW - 0.004, BD - 0.004), new T.MeshStandardMaterial({ map: bbTex, roughness: 0.65 }));
  bbTop.rotation.x = -Math.PI / 2; bbTop.position.set(0, BT + 0.0004, BZ); S.scene.add(bbTop);
  S.contact(BW + 0.08, BD + 0.08, 0, BZ, 0.5);
  var LY = BT + 0.006;

  // ---------- resistors on the board (real colour bands from the value)
  var BAND = ['#111111', '#6b3a1e', '#c4231c', '#e8761e', '#e9c81a', '#2c8a3a', '#2747a8', '#7a3aa8', '#8a8a8a', '#f2f2f2'];
  var BNAME = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white'];
  function bandsOf(r) {
    var e = Math.floor(Math.log(r) / Math.LN10) - 1, d = Math.round(r / Math.pow(10, e));
    if (d >= 100) { d = Math.round(d / 10); e += 1; }
    return [Math.floor(d / 10), d % 10, Math.max(0, Math.min(9, e))];
  }
  var resGroup = new T.Group(); S.scene.add(resGroup);
  var resTerms = [];
  PL.parts.filter(function (q) { return q.r < 1e8; }).forEach(function (q, i) {
    var bd = bandsOf(q.r);
    var tex = S.canvasTex(64, 400, function (x, w, h) {
      x.fillStyle = '#d9bf8c'; x.fillRect(0, 0, w, h);
      [[0.24, BAND[bd[0]]], [0.37, BAND[bd[1]]], [0.5, BAND[bd[2]]], [0.78, '#c9a23a']].forEach(function (b) {
        x.fillStyle = b[1]; x.fillRect(0, h * (1 - b[0]) - 16, w, 32);
      });
    });
    var g = new T.Group(); resGroup.add(g);
    var body = S.mesh(new T.CylinderGeometry(0.0019, 0.0019, 0.015, 20), new T.MeshStandardMaterial({ map: tex, roughness: 0.55 }));
    body.rotation.z = Math.PI / 2; g.add(body);
    [-1, 1].forEach(function (sg) {
      var ld = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.007, 8), M.chrome, false);
      ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.011; g.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.006, 8), M.chrome, false);
      dn.position.set(sg * 0.0145, -0.003, 0); g.add(dn);
    });
    g.position.set(-0.115 + i * 0.075, LY, BZ - 0.035);
    var lb = S.label(q.tag + ' ' + ohm(q.r), { w: 0.034, ratio: 0.26, color: '#3d3528', weight: 700 });
    lb.rotation.x = -Math.PI / 2; lb.position.set(g.position.x, BT + 0.0008, BZ - 0.049); S.scene.add(lb);
    resTerms.push(g);
  });

  // ---------- the lab's own component
  var comp = new T.Group(); S.scene.add(comp); comp.position.set(0.04, LY, BZ + 0.012);
  var compGlow = null;
  if (PL.comp === 'to92') {
    var caseM = new T.MeshStandardMaterial({ color: 0x14151a, roughness: 0.42 });
    var body = S.mesh(new T.CylinderGeometry(0.0023, 0.0023, 0.0048, 24, 1, false, -0.7, Math.PI * 2 - 1.4), caseM);
    body.position.y = 0.0024; comp.add(body);
    var flat = S.mesh(new T.BoxGeometry(0.0038, 0.0048, 0.0004), caseM); flat.position.set(0, 0.0024, 0.00185); comp.add(flat);
    var cap = S.mesh(new T.SphereGeometry(0.0023, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), caseM);
    cap.scale.y = 0.5; cap.position.y = 0.0048; comp.add(cap);
    [-0.0013, 0, 0.0013].forEach(function (dx) {
      var lg = S.mesh(new T.CylinderGeometry(0.00035, 0.00035, 0.007, 8), M.chrome, false);
      lg.position.set(dx, -0.0035, 0); comp.add(lg);
    });
  } else if (PL.comp === 'dip8') {
    var dipM = new T.MeshStandardMaterial({ color: 0x15161a, roughness: 0.4 });
    var dip = S.rounded(0.0098, 0.0064, 0.0035, 0.0006, dipM);
    dip.rotation.x = -Math.PI / 2; dip.position.y = 0.00175; comp.add(dip);
    var notch = S.mesh(new T.CylinderGeometry(0.0011, 0.0011, 0.0012, 14, 1, false, 0, Math.PI), new T.MeshStandardMaterial({ color: 0x2a2c32, roughness: 0.5 }), false);
    notch.position.set(-0.0049, 0.0035, 0); comp.add(notch);
    var dot = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.0004, 10), new T.MeshStandardMaterial({ color: 0x3a3d45 }), false);
    dot.position.set(-0.0036, 0.0036, -0.002); comp.add(dot);
    var i2, sg2;
    for (i2 = 0; i2 < 4; i2++) {
      for (sg2 = -1; sg2 <= 1; sg2 += 2) {
        var pin = S.mesh(new T.BoxGeometry(0.0006, 0.005, 0.0003), M.chrome, false);
        pin.position.set(-0.0038 + i2 * 0.00254, -0.0015, sg2 * 0.0036); comp.add(pin);
      }
    }
  } else if (PL.comp === 'zener') {
    var zm = new T.MeshStandardMaterial({ color: 0x1a1b1f, roughness: 0.35 });
    var zb = S.mesh(new T.CylinderGeometry(0.0021, 0.0021, 0.0085, 24), zm); zb.rotation.z = Math.PI / 2; comp.add(zb);
    var band = S.mesh(new T.CylinderGeometry(0.00215, 0.00215, 0.0014, 24), new T.MeshStandardMaterial({ color: 0xcfd3d6, roughness: 0.3, metalness: 0.7 }));
    band.rotation.z = Math.PI / 2; band.position.x = -0.0028; comp.add(band);
    [-1, 1].forEach(function (sg) {
      var ld = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.009, 8), M.chrome, false);
      ld.rotation.z = Math.PI / 2; ld.position.x = sg * 0.0087; comp.add(ld);
      var dn = S.mesh(new T.CylinderGeometry(0.0004, 0.0004, 0.007, 8), M.chrome, false);
      dn.position.set(sg * 0.0132, -0.0035, 0); comp.add(dn);
    });
  } else if (PL.comp === 'solar') {
    comp.position.set(0.0, LY + 0.001, BZ + 0.005);
    var cellTex = S.canvasTex(512, 512, function (x, w, h) {
      var g = x.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#16307a'); g.addColorStop(1, '#0d1f55');
      x.fillStyle = g; x.fillRect(0, 0, w, h);
      x.strokeStyle = '#c9ccd1'; x.lineWidth = 5;
      var i; for (i = 1; i < 14; i++) { x.beginPath(); x.moveTo(20, i * h / 14); x.lineTo(w - 20, i * h / 14); x.stroke(); }
      x.lineWidth = 14; x.beginPath(); x.moveTo(w * 0.28, 16); x.lineTo(w * 0.28, h - 16); x.stroke();
      x.beginPath(); x.moveTo(w * 0.72, 16); x.lineTo(w * 0.72, h - 16); x.stroke();
    });
    var cell = S.mesh(new T.BoxGeometry(0.072, 0.0016, 0.072), [M.alu, M.alu, new T.MeshStandardMaterial({ map: cellTex, roughness: 0.22, metalness: 0.2 }), M.alu, M.alu, M.alu]);
    cell.position.y = 0.0008; comp.add(cell);
    // the lamp above it
    var lampG = new T.Group(); S.scene.add(lampG); lampG.position.set(0, 0, BZ - 0.005);
    var stem = S.mesh(new T.CylinderGeometry(0.006, 0.008, 0.2, 14), M.iron); stem.position.set(0.0, 0.1, -0.1); lampG.add(stem);
    var armL = S.mesh(new T.CylinderGeometry(0.005, 0.005, 0.1, 12), M.iron); armL.rotation.x = Math.PI / 2; armL.position.set(0, 0.2, -0.05); lampG.add(armL);
    var shade = S.mesh(new T.ConeGeometry(0.035, 0.03, 24, 1, true), new T.MeshStandardMaterial({ color: 0xd8d4c8, roughness: 0.4, metalness: 0.3, side: T.DoubleSide }));
    shade.rotation.x = Math.PI; shade.position.set(0, 0.19, 0.0); lampG.add(shade);
    var bulbM = new T.MeshStandardMaterial({ color: 0xfff3cf, emissive: 0xffe9a8, emissiveIntensity: 2.4, roughness: 0.2 });
    var bulb = S.mesh(new T.SphereGeometry(0.014, 20, 14), bulbM, false, false); bulb.position.set(0, 0.176, 0); lampG.add(bulb);
    var lampLight = new T.PointLight(0xfff0d0, 1.6, 0.8); lampLight.position.set(0, 0.16, BZ - 0.005); S.scene.add(lampLight);
    S.addApparatus('lamp', lampG, 'Filament lamp', 'The light source. It stays where it is for the whole experiment: the photocurrent must not change while the load is varied.');
    var potG = new T.Group(); S.scene.add(potG); potG.position.set(0.15, 0, BZ);
    var pcase = S.mesh(new T.CylinderGeometry(0.019, 0.019, 0.012, 28), M.bakelite); pcase.position.y = 0.006; potG.add(pcase);
    var pdial = S.mesh(new T.CylinderGeometry(0.014, 0.0155, 0.012, 28), new T.MeshStandardMaterial({ color: 0x23242a, roughness: 0.45 })); pdial.position.y = 0.018; potG.add(pdial);
    var pmark = S.mesh(new T.BoxGeometry(0.0018, 0.0012, 0.013), M.white, false); pmark.position.set(0, 0.0242, 0.006); potG.add(pmark);
    S.contact(0.07, 0.07, 0.15, BZ, 0.5);
    compGlow = { pot: potG, mark: pmark };
    S.addApparatus('pot', potG, 'Load potentiometer', 'The load across the cell. Turning it takes the cell from almost a short circuit to almost an open circuit.');
  }
  if (PL.comp !== 'solar') S.contact(0.05, 0.05, comp.position.x, comp.position.z, 0.35, BT);

  // ---------- variable DC bench supply
  var PSW = 0.24, PSH = 0.12, PSD = 0.17, PW = PSW - 0.014, PH = PSH - 0.014, VMAXS = 30;
  var psu = new T.Group(); S.scene.add(psu); psu.position.set(0.45, 0, -0.36); psu.rotation.y = -0.3;
  var caseM2 = new T.MeshStandardMaterial({ color: 0xd9d5cb, roughness: 0.5, metalness: 0.15 });
  var cs = S.rounded(PSW, PSD, PSH, 0.012, caseM2); cs.rotation.x = -Math.PI / 2; cs.position.y = PSH / 2 + 0.004; psu.add(cs);
  [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (f) {
    var ft = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.004, 16), M.rubber);
    ft.position.set(f[0] * (PSW / 2 - 0.02), 0.002, f[1] * (PSD / 2 - 0.02)); psu.add(ft);
  });
  var vsl; for (vsl = 0; vsl < 9; vsl++) { var slot = S.mesh(new T.BoxGeometry(0.004, 0.0012, 0.07), M.black, false); slot.position.set(-0.06 + vsl * 0.015, PSH + 0.0085, -0.03); psu.add(slot); }
  var FZ = PSD / 2 + 0.0062, KX = -0.018, KY = -0.008;
  var panelTex = S.canvasTex(1100, Math.round(1100 * PH / PW), function (x, w, h) {
    var X = function (u) { return (u / PW + 0.5) * w; }, Y = function (v) { return (0.5 - v / PH) * h; }, k = w / PW;
    x.fillStyle = '#2b323d'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.12)'; x.lineWidth = 3; x.strokeRect(10, 10, w - 20, h - 20);
    x.fillStyle = '#f1efe8'; x.font = '700 38px "Public Sans", sans-serif'; x.fillText('REGULATED DC POWER SUPPLY', 40, 68);
    x.font = '500 25px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('0 – ' + VMAXS + ' V  ·  1 A max  ·  dual ±15 V rails for the op-amp', 40, 104);
    var cx = X(KX), cy = Y(KY), R = 0.025 * k, i, th;
    x.strokeStyle = '#f1efe8'; x.fillStyle = '#f1efe8';
    for (i = 0; i <= 30; i++) {
      th = (225 - 270 * i / 30) * Math.PI / 180;
      var big = i % 5 === 0, r0 = big ? R + 22 : R + 12;
      x.lineWidth = big ? 4 : 2; x.beginPath();
      x.moveTo(cx + Math.cos(th) * R, cy - Math.sin(th) * R); x.lineTo(cx + Math.cos(th) * r0, cy - Math.sin(th) * r0); x.stroke();
      if (big) { x.font = '600 25px "Public Sans", sans-serif'; x.textAlign = 'center';
        x.fillText(String(Math.round(i / 30 * VMAXS)), cx + Math.cos(th) * (R + 46), cy - Math.sin(th) * (R + 46) + 9); }
    }
    x.textAlign = 'center'; x.font = '700 26px "Public Sans", sans-serif'; x.fillText('VOLTAGE  (V)', cx, Y(-0.046));
    x.fillText('POWER', X(-0.088), Y(-0.046)); x.font = '600 22px "Public Sans", sans-serif'; x.fillText('ON', X(-0.088), Y(0.026));
    x.font = '700 26px "Public Sans", sans-serif'; x.fillText('OUTPUT', X(0.072), Y(0.022));
    x.font = '700 40px "Public Sans", sans-serif'; x.fillStyle = '#9aa3b2'; x.fillText('−', X(0.055), Y(-0.04));
    x.fillStyle = '#ff7a6b'; x.fillText('+', X(0.09), Y(-0.04));
    x.textAlign = 'left';
  });
  var fascia = S.mesh(new T.BoxGeometry(PW, PH, 0.004), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: panelTex, roughness: 0.45 }), M.grey]);
  fascia.position.set(0, 0.004 + PSH / 2, FZ - 0.002); psu.add(fascia);
  function pp(u, v, dz) { return new T.Vector3(u, 0.004 + PSH / 2 + v, FZ + (dz || 0)); }
  var knurl = S.canvasTex(256, 32, function (x, w, h) { x.fillStyle = '#16171a'; x.fillRect(0, 0, w, h); x.fillStyle = '#3a3c42'; var i; for (i = 0; i < w; i += 8) x.fillRect(i, 0, 3, h); });
  var mainKnob = new T.Group(); mainKnob.position.copy(pp(KX, KY)); psu.add(mainKnob);
  var skirt = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.004, 36), M.bakelite); skirt.rotation.x = Math.PI / 2; skirt.position.z = 0.002; mainKnob.add(skirt);
  var kb = S.mesh(new T.CylinderGeometry(0.0145, 0.016, 0.016, 36), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); kb.rotation.x = Math.PI / 2; kb.position.z = 0.012; mainKnob.add(kb);
  var kc = S.mesh(new T.CylinderGeometry(0.0135, 0.0135, 0.0015, 36), M.chrome); kc.rotation.x = Math.PI / 2; kc.position.z = 0.0205; mainKnob.add(kc);
  var ptr = S.mesh(new T.BoxGeometry(0.0022, 0.016, 0.0012), M.white, false); ptr.position.set(0, 0.009, 0.0215); mainKnob.add(ptr);
  function mainAngle(v) { return 3 * Math.PI / 4 - 1.5 * Math.PI * clamp(v / VMAXS, 0, 1); }
  mainKnob.rotation.z = mainAngle(0);
  var rocker = S.rounded(0.016, 0.024, 0.008, 0.003, M.bakelite); rocker.position.copy(pp(-0.088, -0.018, 0.004)); psu.add(rocker);
  var rmark = S.mesh(new T.BoxGeometry(0.0018, 0.008, 0.001), M.white, false); rmark.position.set(0, 0.006, 0.0045); rocker.add(rmark);
  var lampM = new T.MeshStandardMaterial({ color: 0x5a1410, roughness: 0.3 });
  var pilot = S.mesh(new T.SphereGeometry(0.0055, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), lampM);
  pilot.rotation.x = Math.PI / 2; pilot.position.copy(pp(-0.088, 0.012, 0)); psu.add(pilot);
  var bez = S.mesh(new T.TorusGeometry(0.006, 0.0012, 8, 24), M.chrome); bez.position.copy(pp(-0.088, 0.012, 0.0005)); psu.add(bez);
  function setPowerLook() {
    rocker.rotation.x = st.power ? -0.22 : 0.22;
    lampM.color.setHex(st.power ? 0xff3b2a : 0x5a1410);
    lampM.emissive.setHex(st.power ? 0xff2a14 : 0x000000);
    lampM.emissiveIntensity = st.power ? 2.2 : 0;
  }
  setPowerLook();
  function post(u, mat) {
    var g = new T.Group(); g.position.copy(pp(u, -0.012)); psu.add(g);
    var stm = S.mesh(new T.CylinderGeometry(0.0028, 0.0028, 0.02, 14), M.brass); stm.rotation.x = Math.PI / 2; stm.position.z = 0.01; g.add(stm);
    var cp = S.mesh(new T.CylinderGeometry(0.0075, 0.0085, 0.012, 20), mat); cp.rotation.x = Math.PI / 2; cp.position.z = 0.012; g.add(cp);
    var ns = S.mesh(new T.CylinderGeometry(0.0045, 0.0055, 0.004, 16), mat); ns.rotation.x = Math.PI / 2; ns.position.z = 0.02; g.add(ns);
    return g;
  }
  post(0.055, M.blackPlastic); post(0.09, M.red);
  S.contact(0.34, 0.26, psu.position.x, psu.position.z, 0.55);

  // ---------- low-voltage source (0-5 V), for the gate / base / input side
  var NEEDAUX = CTRL.some(function (c) { return c.knob === 'aux' || c.knob === 'aux2'; });
  var aux = new T.Group(); S.scene.add(aux); aux.position.set(-0.42, 0, -0.3); aux.rotation.y = 0.34;
  aux.visible = NEEDAUX;
  var AW = 0.15, AH = 0.08, AD = 0.11, AFZ = AD / 2 + 0.004;
  var acs = S.rounded(AW, AD, AH, 0.008, new T.MeshStandardMaterial({ color: 0x30353d, roughness: 0.45 }));
  acs.rotation.x = -Math.PI / 2; acs.position.y = AH / 2 + 0.003; aux.add(acs);
  var auxTex = S.canvasTex(700, Math.round(700 * (AH - 0.01) / (AW - 0.01)), function (x, w, h) {
    x.fillStyle = '#20242b'; x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.14)'; x.lineWidth = 3; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#f1efe8'; x.font = '700 32px "Public Sans", sans-serif'; x.fillText('LOW-VOLTAGE SOURCE', 26, 54);
    x.font = '500 23px "Public Sans", sans-serif'; x.fillStyle = '#c7ccd6'; x.fillText('−5 V … +5 V  ·  10 mA', 26, 88);
    x.font = '700 24px "Public Sans", sans-serif'; x.fillStyle = '#f1efe8'; x.fillText('SET', 72, h - 30);
    x.fillStyle = '#ff7a6b'; x.fillText('+', w - 96, h - 30); x.fillStyle = '#9aa3b2'; x.fillText('−', w - 50, h - 30);
  });
  var auxFas = S.mesh(new T.BoxGeometry(AW - 0.01, AH - 0.01, 0.003), [M.grey, M.grey, M.grey, M.grey, new T.MeshStandardMaterial({ map: auxTex, roughness: 0.45 }), M.grey]);
  auxFas.position.set(0, AH / 2 + 0.003, AFZ - 0.0015); aux.add(auxFas);
  var auxKnob = new T.Group(); auxKnob.position.set(-0.03, AH / 2 + 0.013, AFZ + 0.001); aux.add(auxKnob);
  var ak = S.mesh(new T.CylinderGeometry(0.011, 0.012, 0.012, 30), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); ak.rotation.x = Math.PI / 2; ak.position.z = 0.007; auxKnob.add(ak);
  var akm = S.mesh(new T.BoxGeometry(0.0018, 0.011, 0.001), M.white, false); akm.position.set(0, 0.006, 0.0135); auxKnob.add(akm);
  var auxKnob2 = new T.Group(); auxKnob2.position.set(0.028, AH / 2 + 0.013, AFZ + 0.001); aux.add(auxKnob2);
  var ak2 = S.mesh(new T.CylinderGeometry(0.009, 0.01, 0.01, 26), new T.MeshStandardMaterial({ map: knurl, roughness: 0.45 })); ak2.rotation.x = Math.PI / 2; ak2.position.z = 0.006; auxKnob2.add(ak2);
  var akm2 = S.mesh(new T.BoxGeometry(0.0016, 0.009, 0.001), M.white, false); akm2.position.set(0, 0.005, 0.0115); auxKnob2.add(akm2);
  if (NEEDAUX) S.contact(0.22, 0.18, aux.position.x, aux.position.z, 0.5);

  // ---------- two digital multimeters
  function dmm(x, z, rotY, spec) {
    var g = new T.Group(); S.scene.add(g); g.position.set(x, 0, z); g.rotation.y = rotY;
    var W = 0.14, D = 0.17, Hh = 0.052;
    var body = S.rounded(W, D, Hh, 0.01, new T.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.5 }));
    body.rotation.x = -Math.PI / 2; body.position.y = Hh / 2 + 0.002; g.add(body);
    var boot = S.rounded(W + 0.012, D + 0.012, 0.012, 0.012, new T.MeshStandardMaterial({ color: 0xd9682a, roughness: 0.8 }));
    boot.rotation.x = -Math.PI / 2; boot.position.y = 0.007; g.add(boot);
    var lcd = S.liveTex(640, 260);
    var face = new T.Group(); face.rotation.x = -Math.PI / 2 + 0.16; face.position.set(0, Hh + 0.004, 0.0); g.add(face);
    var plate = S.canvasTex(700, 900, function (cx, w, h) {
      cx.fillStyle = '#30353d'; cx.fillRect(0, 0, w, h);
      cx.fillStyle = '#f1efe8'; cx.font = '700 34px "Public Sans", sans-serif'; cx.textAlign = 'center';
      cx.fillText('DIGITAL MULTIMETER', w / 2, 56);
      cx.font = '500 24px "Public Sans", sans-serif'; cx.fillStyle = '#aab1bc'; cx.fillText('4½ digit  ·  auto range  ·  CAT II 600 V', w / 2, 92);
      cx.strokeStyle = '#8d949f'; cx.lineWidth = 4; cx.beginPath(); cx.arc(w / 2, h * 0.64, 150, 0, Math.PI * 2); cx.stroke();
      var labels = ['OFF', 'DC V', 'AC V', 'DC mA', 'DC µA', 'Ω', 'TEST'];
      cx.font = '700 26px "Public Sans", sans-serif'; cx.fillStyle = '#f1efe8';
      labels.forEach(function (t, i) {
        var a = -Math.PI / 2 + (i - 3) * 0.62;
        cx.fillText(t, w / 2 + Math.cos(a) * 190, h * 0.64 + Math.sin(a) * 190 + 9);
      });
      cx.fillStyle = '#ff7a6b'; cx.beginPath(); cx.arc(w * 0.68, h * 0.95, 26, 0, Math.PI * 2); cx.fill();
      cx.fillStyle = '#1b1b1b'; cx.beginPath(); cx.arc(w * 0.32, h * 0.95, 26, 0, Math.PI * 2); cx.fill();
      cx.textAlign = 'left';
    });
    var pf = new T.Mesh(new T.PlaneGeometry(0.128, 0.165), new T.MeshStandardMaterial({ map: plate, roughness: 0.5 }));
    pf.position.set(0, 0, 0.0005); face.add(pf);
    var scr = new T.Mesh(new T.PlaneGeometry(0.1, 0.041), new T.MeshBasicMaterial({ map: lcd, toneMapped: false }));
    scr.position.set(0, 0.052, 0.0012); face.add(scr);
    var bezl = S.mesh(new T.BoxGeometry(0.108, 0.048, 0.002), new T.MeshStandardMaterial({ color: 0x15171b, roughness: 0.5 }), false);
    bezl.position.set(0, 0.052, 0.0002); face.add(bezl);
    var dialG = new T.Group(); dialG.position.set(0, -0.0045, 0.0015); face.add(dialG);
    var dk = S.mesh(new T.CylinderGeometry(0.019, 0.02, 0.006, 30), new T.MeshStandardMaterial({ color: 0x1b1d22, roughness: 0.45 }));
    dk.rotation.x = Math.PI / 2; dk.position.z = 0.003; dialG.add(dk);
    var dm = S.mesh(new T.BoxGeometry(0.0028, 0.016, 0.001), M.white, false); dm.position.set(0, 0.009, 0.0065); dialG.add(dm);
    var jr = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 18), M.red); jr.rotation.x = Math.PI / 2; jr.position.set(0.018, -0.0655, 0.003); face.add(jr);
    var jb = S.mesh(new T.CylinderGeometry(0.0055, 0.0055, 0.006, 18), M.blackPlastic); jb.rotation.x = Math.PI / 2; jb.position.set(-0.018, -0.0655, 0.003); face.add(jb);
    g.userData = { lcd: lcd, dial: dialG, red: jr, black: jb, last: '' };
    S.contact(0.19, 0.22, x, z, 0.5);
    var o = { group: g, spec: spec };
    o.draw = function (txt, fn, on) {
      var key = txt + '|' + fn + '|' + on;
      if (g.userData.last === key) return;
      g.userData.last = key;
      lcd.draw(function (cx, w, h) {
        var gr = cx.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#c3ccb0'); gr.addColorStop(1, '#a3b092');
        cx.fillStyle = gr; cx.fillRect(0, 0, w, h);
        if (!on) { cx.fillStyle = '#6e7a62'; cx.font = '600 44px "Public Sans", sans-serif'; cx.textAlign = 'center'; cx.fillText('OFF', w / 2, h / 2 + 16); return; }
        cx.font = '700 120px "JetBrains Mono", monospace'; cx.textAlign = 'right';
        cx.fillStyle = 'rgba(0,0,0,.07)'; cx.fillText('-8.8888', w - 120, 160);
        cx.fillStyle = '#171d13'; cx.fillText(txt, w - 120, 160);
        cx.textAlign = 'left'; cx.font = '700 46px "Public Sans", sans-serif'; cx.fillText(fn, w - 112, 160);
        cx.font = '600 32px "Public Sans", sans-serif'; cx.fillStyle = '#2c3526'; cx.fillText('AUTO', 24, 56);
      });
    };
    o.draw('0.000', spec.unit, false);
    return o;
  }
  var dm1 = dmm(-0.26, -0.3, 0.3, PL.m1), dm2 = dmm(0.1, -0.33, -0.08, PL.m2);

  // ---------- wiring
  function lift(v, dy) { return new T.Vector3(v.x, v.y + dy, v.z); }
  var psPos = wpos(psu, 0.09, 0.004 + PSH / 2 - 0.012, FZ + 0.021), psNeg = wpos(psu, 0.055, 0.004 + PSH / 2 - 0.012, FZ + 0.021);
  S.wire([arr(psPos), [psPos.x + 0.02, 0.03, psPos.z + 0.04], [0.16, 0.03, BZ - BD / 2 - 0.02], [0.14, 0.016, BZ - BD / 2 + 0.006]], 'red');
  S.wire([arr(psNeg), [psNeg.x + 0.03, 0.02, psNeg.z + 0.06], [0.2, 0.008, BZ + 0.06], [-0.14, 0.012, BZ + BD / 2 - 0.006]], 'black');
  if (NEEDAUX) {
    var axp = wpos(aux, -0.04, AH / 2, AFZ + 0.012), axn = wpos(aux, 0.04, AH / 2, AFZ + 0.012);
    S.wire([arr(axp), [axp.x + 0.04, 0.03, axp.z + 0.05], [-0.14, 0.016, BZ - BD / 2 + 0.006]], 'gold');
    S.wire([arr(axn), [axn.x + 0.04, 0.012, axn.z + 0.07], [-0.1, 0.012, BZ + BD / 2 - 0.006]], 'black');
  }
  function mt(o, which) { var w = new T.Vector3(); o.group.updateMatrixWorld(true); o.group.userData[which].getWorldPosition(w); return w; }
  [[dm1, -0.06, 'blue'], [dm2, 0.06, 'gold']].forEach(function (q) {
    var r = mt(q[0], 'red'), b = mt(q[0], 'black');
    S.wire([arr(r), [r.x + 0.02, 0.03, r.z + 0.06], [q[1], 0.016, BZ - BD / 2 + 0.006]], q[2]);
    S.wire([arr(b), [b.x - 0.01, 0.02, b.z + 0.07], [q[1] + 0.02, 0.012, BZ + BD / 2 - 0.006]], 'black');
  });

  S.addApparatus('psu', psu, 'Regulated DC bench supply (0–' + VMAXS + ' V)', 'The VOLTAGE knob sets the supply; the POWER rocker switches it on and the pilot lamp shows that it is live. Always start at zero.');
  if (NEEDAUX) S.addApparatus('aux', aux, 'Low-voltage source (−5 V … +5 V)', 'A small, finely adjustable source for the input, gate or base side of the circuit, so it can be set without touching the main supply.');
  S.addApparatus('bb', bb, 'Solderless breadboard', '830 tie points in two banks with a channel down the middle for the integrated circuits, and a power rail along each side.');
  if (PL.parts.length) S.addApparatus('res', resGroup, 'Carbon resistors', PL.parts.filter(function (q) { return q.r < 1e8; }).map(function (q) { return q.tag + ' = ' + ohm(q.r) + ' (bands ' + bandsOf(q.r).map(function (i) { return BNAME[i]; }).join('-') + '-gold, ±5 %)'; }).join('.  '));
  S.addApparatus('comp', comp, PL.compName, PL.wiring);
  S.addApparatus('dm1', dm1.group, 'Digital multimeter 1 — ' + PL.m1.label, 'Range ' + PL.m1.fn + ', least count ' + PL.m1.lc + ' ' + PL.m1.unit + '. Its leads are already on the right two points of the circuit.');
  S.addApparatus('dm2', dm2.group, 'Digital multimeter 2 — ' + PL.m2.label, 'Range ' + PL.m2.fn + ', least count ' + PL.m2.lc + ' ' + PL.m2.unit + '.');
  S.addApparatus('book', S.book.group, 'Lab record book', 'Every reading you take is written here, as in a real practical file.');

  var hud1 = S.hudCard(PL.m1.label), hud2 = S.hudCard(PL.m2.label), hudS = S.hudCard('Setting');

  // =============================================================================================== human actions
  function knobOf(c) { return c.knob === 'main' ? mainKnob : c.knob === 'aux2' ? auxKnob2 : c.knob === 'pot' ? (compGlow && compGlow.pot) : auxKnob; }
  function knobFront(c) {
    if (c.knob === 'main') return wpos(psu, KX, 0.004 + PSH / 2 + KY, FZ + 0.024);
    if (c.knob === 'pot') return new T.Vector3(0.15, 0.03, BZ + 0.02);
    return wpos(aux, c.knob === 'aux2' ? 0.028 : -0.03, AH / 2 + 0.013, AFZ + 0.016);
  }
  function setLook(i) {
    var c = CTRL[i], k = knobOf(c);
    if (!k) return;
    var f = (st.idx[i] + 1) / Math.max(1, c.vals.length);
    if (c.knob === 'main') k.rotation.z = mainAngle(st.set[i]);
    else if (c.knob === 'pot') k.rotation.y = -3 * f;
    else k.rotation.z = 3 * Math.PI / 4 - 1.5 * Math.PI * clamp((st.set[i] + 5) / 10, 0, 1);
  }
  CTRL.forEach(function (c, i) { setLook(i); });

  function turnTo(i, value) {
    var c = CTRL[i];
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    var j = 0, best = 1e30, k;
    for (k = 0; k < c.vals.length; k++) if (Math.abs(c.vals[k] - value) < best) { best = Math.abs(c.vals[k] - value); j = k; }
    if (j === st.idx[i]) return Promise.resolve();
    var from = st.set[i], to = c.vals[j], pt = knobFront(c);
    return S.hand.pinchMove(pt, function () { return pt; }, function (kk) {
      st.set[i] = from + (to - from) * kk; st.idx[i] = j; setLook(i);
    }, { mode: 'front', ms: 420 + 260 * Math.min(3, Math.abs(j - st.idx[i])), reachMs: 560 })
      .then(function () { st.set[i] = to; st.idx[i] = j; setLook(i); S.render(); });
  }
  function togglePower(on) {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return Promise.resolve(); }
    if (on === st.power) return Promise.resolve();
    return S.hand.tap(rocker, 'front').then(function () {
      st.power = on; setPowerLook(); S.click(900, 0.05);
      S.say(on ? 'Supply on. The pilot lamp is lit and both meters have woken up.' : 'Supply off.');
      S.render();
    });
  }

  function rowNow() {
    var v = live(), q = liveQ(), row = { set: st.set[0], m1: meterVal(PL.m1), m2: meterVal(PL.m2) };
    (PL.extra || []).forEach(function (e) { row[e.key] = round(e.get(v, q), e.digits); });
    if (PL.derive) PL.derive(row);
    return row;
  }
  function record() {
    if (S.hand.busy) { S.say('Wait for the hand to finish.'); return; }
    if (!st.power) { S.say('Switch the supply on first.'); return; }
    var i, same;
    for (i = 0; i < S.rows.length; i++) {
      same = true;
      for (var j = 0; j < CTRL.length; j++) if (Math.abs((S.rows[i]['c' + j] === undefined ? S.rows[i].set : S.rows[i]['c' + j]) - st.set[j]) > 1e-9) same = false;
      if (same) { S.say('You already have a reading at this setting. Turn a knob to a new one.'); return; }
    }
    var row = rowNow();
    for (i = 0; i < CTRL.length; i++) row['c' + i] = st.set[i];
    S.addRow(row);
    S.say('Written in your record book: ' + fmt(row.m1, PL.m1.digits) + ' ' + PL.m1.unit + ' and ' +
      fmt(row.m2, PL.m2.digits) + ' ' + PL.m2.unit + '.');
  }
  function enough() { return S.rows.length >= PL.need; }

  return {
    camera: { pos: [0.14, 0.74, 1.04], look: [0.04, 0.03, -0.18] },
    views: {
      psu: [[0.6, 0.24, 0.0], [0.44, 0.07, -0.3]], aux: [[-0.4, 0.2, 0.0], [-0.42, 0.06, -0.28]],
      bb: [[0.0, 0.4, 0.36], [0.0, 0.01, -0.04]], comp: [[0.07, 0.12, 0.09], [0.04, 0.015, -0.02]],
      res: [[-0.08, 0.14, 0.1], [-0.08, 0.015, -0.05]], pot: [[0.18, 0.15, 0.12], [0.15, 0.02, -0.03]],
      dm1: [[-0.25, 0.17, -0.14], [-0.26, 0.05, -0.3]], dm2: [[0.1, 0.17, -0.17], [0.1, 0.05, -0.32]],
      bench: [[0.08, 0.46, 0.7], [0.0, 0.03, -0.18]], book: [[-0.42, 0.44, 0.52], [-0.5, 0.0, 0.08]],
    },
    theory: {
      principle: S.lab.theory,
      formula: BASE === 'bjt-ce-current-gain' ? 'β = ΔI_C / ΔI_B' :
        BASE === 'jfet-transfer-characteristic' ? 'I_D = I_DSS (1 − V_GS/V_P)²' :
        BASE === 'mosfet-transfer-characteristic' ? 'I_D = (k/2)(V_GS − V_th)²' :
        BASE === 'zener-shunt-regulator' ? 'V_o = (V_in/R_S + V_Z/r_z) / (1/R_S + 1/r_z + 1/R_L)' :
        BASE === 'solar-cell-characteristic' ? 'FF = P_max / (I_sc V_oc)' :
        BASE === 'opamp-summing-amplifier' ? 'V_o = −R_f (V_1/R_1 + V_2/R_2 + V_3/R_3)' : 'V_o = −(R_f/R_1) V_in',
      formulaNote: 'All the numbers on this bench come from the lab\'s own kernel; the apparatus is the shared ' +
        'electronics bench. ' + (SAMPLE ? 'This specimen: ' + SAMPLE + '.' : ''),
      more: ['How it is wired: ' + PL.wiring],
      precautions: S.lab.safety + ' Start with the knob at zero, and read both meters only after the pilot lamp is lit.',
    },
    book: {
      title: 'Expt. — ' + S.lab.title,
      lines: ['Aim: ' + S.lab.aim, PL.wiring,
        'Meter 1: ' + PL.m1.fn + ', least count ' + PL.m1.lc + ' ' + PL.m1.unit,
        'Meter 2: ' + PL.m2.fn + ', least count ' + PL.m2.lc + ' ' + PL.m2.unit,
        'Precautions: knob to zero before switching on; one setting changed at a time.'],
      columns: [{ label: 'S.No', get: function (r, i) { return i + 1; } }].concat(PL.cols.map(function (c) {
        return { label: c.label, get: function (r) { return fmt(r[c.key], c.digits); } };
      })),
    },
    graph: {
      x: PL.graph.x, y: PL.graph.y, xlabel: PL.graph.xlabel, ylabel: PL.graph.ylabel,
      line: function (pts) {
        var q = pts.slice().sort(function (a, b) { return a[0] - b[0]; });
        return function (x) {
          var i;
          if (x <= q[0][0]) return q[0][1];
          for (i = 0; i < q.length - 1; i++) {
            if (x <= q[i + 1][0]) {
              var a = q[i], b = q[i + 1];
              return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]);
            }
          }
          return q[q.length - 1][1];
        };
      },
    },
    result: function (rows) { return rows.length < 2 ? null : PL.result(rows); },
    tol: 0.03,
    resultNote: PL.resultNote,
    chips: PL.chips,
    viva: PL.viva,
    askState: function () {
      var v = live(), out = {
        supply_on: st.power, readings_taken: S.rows.length,
        circuit: PL.wiring, specimen: SAMPLE || PL.compName,
      };
      out[PL.m1.label] = round(meterVal(PL.m1), PL.m1.digits + 1) + ' ' + PL.m1.unit;
      out[PL.m2.label] = round(meterVal(PL.m2), PL.m2.digits + 1) + ' ' + PL.m2.unit;
      CTRL.forEach(function (c) { out[c.label] = round(st.set[CTRL.indexOf(c)], 3) + ' ' + c.unit; });
      (PL.extra || []).forEach(function (e) { out[e.label] = round(e.get(v, liveQ()), e.digits); });
      return out;
    },

    steps: [
      { id: 'setup', title: 'Set up', view: 'bench', render: function (u) {
          u.h2('Check the circuit and switch on');
          u.p(PL.wiring);
          u.task('1. Check the circuit on the board', st.checked,
            st.checked ? 'Component and resistors in the right places' : 'Look at the component and its leads')
            .add(u.button(st.checked ? 'Checked' : 'Check the circuit', function () {
              st.checked = true; S.focus('comp');
              S.say(PL.compName + '. ' + PL.wiring);
              S.render();
            }, !st.checked, st.checked));
          u.task('2. Controls at zero, then switch the supply on', st.power,
            st.power ? 'Supply on; both meters reading' : 'The hand presses the POWER rocker')
            .add(u.row(u.button(st.power ? 'Switch off' : 'Switch on the supply', function () {
              S.focus('psu'); togglePower(!st.power);
            }, !st.power, S.hand.busy)));
          u.note('A circuit is checked before it is powered, never after. Keep one hand off the bench while you ' +
            'look it over, and change only one control at a time once it is live.');
          u.next('Next: take readings', st.checked && st.power);
        },
        ok: function () { return st.checked && st.power; },
        auto: function () { st.checked = true; return togglePower(true); } },
      { id: 'read', title: 'Readings', view: 'bench', render: function (u) {
          u.h2('Set the controls and record both meters');
          u.p('Let the hand turn each control to its next value, then read the two multimeters and write the ' +
            'reading into the record book. At least ' + PL.need + ' readings are needed.');
          CTRL.forEach(function (c, i) {
            var tgt = { v: st.set[i] };
            u.slider(c.label, 0, c.vals.length - 1, 1, function () { return c.vals.indexOf(st.set[i]) < 0 ? st.idx[i] : c.vals.indexOf(st.set[i]); },
              function (k) { tgt.v = c.vals[k]; turnTo(i, c.vals[k]); }, '', 0);
            u.note(c.label + ' is now ' + fmt(st.set[i], c.digits) + ' ' + c.unit + (c.vals.length ? '  ·  ' + c.vals.length + ' settings on this control' : ''));
          });
          u.row(u.button('Record both meters', function () { record(); }, true, S.hand.busy));
          u.live(function () {
            return PL.m1.label + ': ' + fmt(meterVal(PL.m1), PL.m1.digits) + ' ' + PL.m1.unit +
              '  ·  ' + PL.m2.label + ': ' + fmt(meterVal(PL.m2), PL.m2.digits) + ' ' + PL.m2.unit;
          });
          u.h3('Observation table'); u.table();
          if (!enough()) u.p(S.rows.length + ' of at least ' + PL.need + ' readings recorded.');
          u.next('Next: plot and work out the result', enough());
        },
        ok: function () { return enough(); },
        auto: function () {
          var plan = [], i, j, n = CTRL[0].vals.length;
          for (i = 0; i < n; i++) {
            var one = [CTRL[0].vals[i]];
            for (j = 1; j < CTRL.length; j++) one.push(CTRL[j].vals[(i * (j + 2)) % CTRL[j].vals.length]);
            plan.push(one);
          }
          return plan.reduce(function (pr, one) {
            return pr.then(function () {
              return one.reduce(function (p2, v, k) { return p2.then(function () { return turnTo(k, v); }); }, Promise.resolve())
                .then(record);
            });
          }, Promise.resolve());
        } },
    ],

    tick: function () {
      var on = st.power;
      dm1.draw(on ? fmt(meterVal(PL.m1), PL.m1.digits) : '0.000', PL.m1.unit, on);
      dm2.draw(on ? fmt(meterVal(PL.m2), PL.m2.digits) : '0.000', PL.m2.unit, on);
      hud1.set(on ? fmt(meterVal(PL.m1), PL.m1.digits) + ' ' + PL.m1.unit : 'off');
      hud2.set(on ? fmt(meterVal(PL.m2), PL.m2.digits) + ' ' + PL.m2.unit : 'off');
      hudS.set(CTRL.map(function (c, i) { return fmt(st.set[i], c.digits) + ' ' + c.unit; }).join('  ·  '));
    },
  };
});
