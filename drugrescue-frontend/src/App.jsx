import React, { useState, useEffect, useRef, useCallback, Component } from 'react';
import { useManifest, useDiseaseData, fuzzyMatch } from './useData.js';

/* ═══ ERROR BOUNDARY — catches crashes, shows error instead of blank ═══ */
class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) {
      return React.createElement('div', {
        style: { padding: 40, textAlign: 'center', fontFamily: 'monospace' }
      },
        React.createElement('h2', { style: { color: '#dc2626' } }, 'Something crashed'),
        React.createElement('pre', {
          style: { background: '#fef2f2', padding: 20, borderRadius: 12, textAlign: 'left', whiteSpace: 'pre-wrap', fontSize: 12, marginTop: 16 }
        }, String(this.state.error?.message || this.state.error)),
        React.createElement('pre', {
          style: { background: '#f5f5f4', padding: 16, borderRadius: 12, textAlign: 'left', whiteSpace: 'pre-wrap', fontSize: 10, marginTop: 8, maxHeight: 300, overflow: 'auto' }
        }, String(this.state.error?.stack || '')),
        React.createElement('button', {
          onClick: function() { window.location.reload(); },
          style: { marginTop: 20, padding: '10px 24px', borderRadius: 10, border: 'none', background: '#1c1917', color: '#fff', fontWeight: 700, cursor: 'pointer' }
        }, 'Reload')
      );
    }
    return this.props.children;
  }
}

/* ═══ MICRO COMPONENTS ═══ */

function Typer(props) {
  var text = props.text;
  var speed = props.speed || 10;
  var onDone = props.onDone;
  var ref = useRef(true);
  var stateArr = useState('');
  var d = stateArr[0];
  var setD = stateArr[1];
  useEffect(function() {
    ref.current = true;
    var i = 0;
    setD('');
    var iv = setInterval(function() {
      if (!ref.current) { clearInterval(iv); return; }
      if (i < text.length) { setD(text.slice(0, i + 1)); i++; }
      else { clearInterval(iv); if (onDone) onDone(); }
    }, speed);
    return function() { ref.current = false; clearInterval(iv); };
  }, [text]);
  return React.createElement('span', null,
    d,
    d.length < text.length ? React.createElement('span', { className: 'caret' }, '|') : null
  );
}

function CountUp(props) {
  var to = props.to;
  var dec = props.d || 1;
  var suffix = props.s || '';
  var stateArr = useState(0);
  var v = stateArr[0];
  var setV = stateArr[1];
  useEffect(function() {
    var t0 = performance.now();
    function f(t) {
      var p = Math.min((t - t0) / 1100, 1);
      setV(to * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(f);
    }
    requestAnimationFrame(f);
  }, [to]);
  return React.createElement(React.Fragment, null, v.toFixed(dec) + suffix);
}

function Bar(props) {
  var pct = props.pct;
  var color = props.color;
  var delay = props.delay || 0;
  var stateArr = useState(0);
  var w = stateArr[0];
  var setW = stateArr[1];
  useEffect(function() {
    var t = setTimeout(function() { setW(pct); }, delay + 100);
    return function() { clearTimeout(t); };
  }, [pct, delay]);
  return React.createElement('div', { className: 'bar-bg' },
    React.createElement('div', { className: 'bar-fill', style: { width: w + '%', background: color } })
  );
}

function ScoreRing(props) {
  var score = props.score;
  var size = props.size || 60;
  var delay = props.delay || 0;
  var stateArr = useState(0);
  var p = stateArr[0];
  var setP = stateArr[1];
  useEffect(function() {
    var t = setTimeout(function() { setP(score / 100); }, delay + 100);
    return function() { clearTimeout(t); };
  }, [score, delay]);
  var r = (size - 8) / 2;
  var circ = 2 * Math.PI * r;
  var col = score >= 70 ? '#059669' : score >= 50 ? '#d97706' : '#dc2626';
  var half = size / 2;
  return React.createElement('svg', { width: size, height: size, style: { flexShrink: 0 } },
    React.createElement('circle', { cx: half, cy: half, r: r, fill: 'none', stroke: '#f1f0ee', strokeWidth: 5 }),
    React.createElement('circle', { cx: half, cy: half, r: r, fill: 'none', stroke: col, strokeWidth: 5, strokeDasharray: circ, strokeDashoffset: circ * (1 - p), strokeLinecap: 'round', transform: 'rotate(-90 ' + half + ' ' + half + ')', style: { transition: 'stroke-dashoffset 1.2s cubic-bezier(.22,1,.36,1)' } }),
    React.createElement('text', { x: half, y: half + 1, textAnchor: 'middle', dominantBaseline: 'central', fill: '#1c1917', fontSize: 18, fontWeight: 900, style: { fontFamily: 'var(--fm)' } }, score)
  );
}


function DebateTimeline(props) {
  var debate = props.debate || [];
  var active = props.active;
  var visState = useState(0);
  var vis = visState[0]; var setVis = visState[1];
  var typState = useState(true);
  var typing = typState[0]; var setTyping = typState[1];
  var skipState = useState(false);
  var skipped = skipState[0]; var setSkipped = skipState[1];
  var ref = useRef(null);

  var advance = useCallback(function() {
    setTyping(false);
    setTimeout(function() {
      setVis(function(c) { if (c < debate.length) { setTyping(true); return c + 1; } return c; });
    }, 400);
  }, [debate.length]);

  useEffect(function() { if (active && debate.length) { setVis(1); setTyping(true); setSkipped(false); } }, [active, debate.length]);
  useEffect(function() { if (ref.current) ref.current.scrollTo({ top: ref.current.scrollHeight, behavior: 'smooth' }); }, [vis, typing]);

  var skipAll = useCallback(function() { setSkipped(true); setTyping(false); setVis(debate.length); }, [debate.length]);

  if (!debate.length) return React.createElement('div', { style: { padding: 20, color: 'var(--t3)', textAlign: 'center', fontSize: 13 } }, 'No debate data available.');

  var entries = debate.slice(0, vis).map(function(e, i) {
    var isAdv = e.side === 'adv';
    var isLast = i === vis - 1;
    var showTyper = isLast && typing && !skipped;
    var spd = e.text.length > 120 ? 5 : 7;

    return React.createElement('div', { key: i, style: { display: 'flex', gap: 12, marginBottom: 16, flexDirection: isAdv ? 'row' : 'row-reverse', animation: 'enter .4s ease both' } },
      React.createElement('div', { style: { width: 34, height: 34, borderRadius: 9, flexShrink: 0, background: isAdv ? '#059669' : '#dc2626', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 11, fontWeight: 800 } }, isAdv ? 'A' : 'S'),
      React.createElement('div', { style: { maxWidth: '80%', padding: '14px 18px', borderRadius: 16, background: isAdv ? 'linear-gradient(135deg,#f0fdf4,#ecfdf5)' : 'linear-gradient(135deg,#fef2f2,#fff1f2)', border: '1.5px solid ' + (isAdv ? '#bbf7d0' : '#fecaca'), borderTopLeftRadius: isAdv ? 4 : 16, borderTopRightRadius: isAdv ? 16 : 4 } },
        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 } },
          React.createElement('span', { style: { fontSize: 10, fontWeight: 800, letterSpacing: .5, textTransform: 'uppercase', color: isAdv ? '#059669' : '#dc2626' } }, isAdv ? 'Advocate' : 'Skeptic'),
          React.createElement('span', { style: { fontSize: 9, fontWeight: 600, color: '#9ca3af', background: 'rgba(255,255,255,.7)', padding: '2px 8px', borderRadius: 99, border: '1px solid #f1f0ee' } }, e.topic)
        ),
        React.createElement('div', { style: { fontSize: 12.5, lineHeight: 1.8, fontFamily: 'var(--fm)', color: isAdv ? '#14532d' : '#7f1d1d', letterSpacing: -.1 } },
          showTyper ? React.createElement(Typer, { text: e.text, speed: spd, onDone: advance }) : e.text
        )
      )
    );
  });

  return React.createElement('div', null,
    React.createElement('div', { ref: ref, style: { maxHeight: 560, overflowY: 'auto', padding: '4px 0' } },
      entries,
      vis >= debate.length && !typing ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 12, margin: '18px 0 4px' } },
        React.createElement('div', { style: { flex: 1, height: 1, background: '#e7e5e4' } }),
        React.createElement('span', { style: { fontSize: 10, fontWeight: 700, color: '#a8a29e', letterSpacing: 1, whiteSpace: 'nowrap' } }, '\u2696 DEBATE CONCLUDED \u2014 ' + debate.length + ' exchanges'),
        React.createElement('div', { style: { flex: 1, height: 1, background: '#e7e5e4' } })
      ) : null
    ),
    vis < debate.length && !skipped ? React.createElement('div', { style: { textAlign: 'right', marginTop: 6 } },
      React.createElement('button', { onClick: skipAll, style: { background: 'none', border: '1px solid var(--bd)', borderRadius: 8, padding: '4px 14px', fontSize: 10, fontWeight: 600, color: 'var(--t3)', cursor: 'pointer', fontFamily: 'var(--ff)' } }, 'Skip to end')
    ) : null
  );
}

function JudgeVerdict(props) {
  var points = props.points || [];
  var topDrug = props.topDrug || '';
  var topVerdict = props.topVerdict;
  var active = props.active;
  var visState = useState(0);
  var vis = visState[0]; var setVis = visState[1];
  var typState = useState(true);
  var typing = typState[0]; var setTyping = typState[1];

  var advance = useCallback(function() {
    setTyping(false);
    setTimeout(function() {
      setVis(function(c) { if (c < points.length) { setTyping(true); return c + 1; } return c; });
    }, 400);
  }, [points.length]);

  useEffect(function() { if (active && points.length) { setVis(1); setTyping(true); } }, [active, points.length]);

  if (!points.length) return null;

  var labelColors = {
    RULING: { bg: '#fef3c7', border: '#f59e0b', color: '#92400e', icon: '\u2696' },
    'EVIDENCE ACCEPTED': { bg: '#d1fae5', border: '#34d399', color: '#065f46', icon: '\u2713' },
    'EVIDENCE REJECTED': { bg: '#fee2e2', border: '#f87171', color: '#991b1b', icon: '\u2717' },
    CONDITIONS: { bg: '#fff7ed', border: '#fb923c', color: '#9a3412', icon: '\u2691' },
    'FINAL ORDER': { bg: '#eff6ff', border: '#60a5fa', color: '#1e40af', icon: '\u279C' },
  };

  var items = points.slice(0, vis).map(function(pt, i) {
    var isObj = pt && typeof pt === 'object' && pt.label;
    var label = isObj ? pt.label : '';
    var text = isObj ? pt.text : (typeof pt === 'string' ? pt : '');
    var lc = labelColors[label] || { bg: '#fafaf9', border: '#e7e5e4', color: '#78350f', icon: '\u25CF' };
    var isLast = i === vis - 1;

    return React.createElement('div', { key: i, style: { marginBottom: 10, animation: 'enter .35s ease both' } },
      label ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 } },
        React.createElement('span', { style: { fontSize: 13 } }, lc.icon),
        React.createElement('span', { style: { fontSize: 9, fontWeight: 800, letterSpacing: 1.5, color: lc.color, textTransform: 'uppercase' } }, label)
      ) : null,
      React.createElement('div', { style: { fontSize: 12, lineHeight: 1.8, fontFamily: 'var(--fm)', color: '#78350f', padding: label ? '10px 14px' : 0, borderRadius: label ? 10 : 0, background: label ? lc.bg : 'transparent', borderLeft: label ? '3px solid ' + lc.border : 'none' } },
        isLast && typing ? React.createElement(Typer, { text: text, speed: 5, onDone: advance }) : text
      )
    );
  });

  var scoreBox = vis >= points.length && !typing && topVerdict ? React.createElement('div', {
    style: { marginTop: 16, padding: '16px 22px', borderRadius: 12, background: 'linear-gradient(135deg,#fef3c7,#fde68a)', border: '2px solid #fbbf24', textAlign: 'center', animation: 'scoreReveal .5s cubic-bezier(.34,1.56,.64,1) both' }
  },
    React.createElement('div', { style: { fontSize: 10, fontWeight: 700, color: '#92400e', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 } }, topDrug + ' Rescue Score'),
    React.createElement('div', { style: { fontSize: 44, fontWeight: 900, color: '#78350f', fontFamily: 'var(--fm)', lineHeight: 1 } }, topVerdict.score, React.createElement('span', { style: { fontSize: 18, fontWeight: 600 } }, ' / 100')),
    React.createElement('div', { style: { fontSize: 11, fontWeight: 700, color: topVerdict.score >= 70 ? '#059669' : '#d97706', marginTop: 6 } }, topVerdict.tier + ' \u2014 Confidence ' + Math.round((topVerdict.confidence || 0) * 100) + '%')
  ) : null;

  return React.createElement('div', null, items, scoreBox);
}

/* ═══ SECTION HEADER ═══ */
function SH(props) {
  return React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 14 } },
    React.createElement('div', { style: { width: 40, height: 40, borderRadius: 10, background: 'var(--ink)', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 13, fontWeight: 800, fontFamily: 'var(--fm)', flexShrink: 0 } }, props.n),
    React.createElement('div', null,
      React.createElement('h2', { style: { fontFamily: 'var(--fs)', fontSize: 28, fontWeight: 400, fontStyle: 'italic', letterSpacing: -.5, lineHeight: 1.1 } }, props.t),
      React.createElement('p', { style: { fontSize: 12, color: 'var(--t2)', marginTop: 2 } }, props.s)
    )
  );
}

/* ═══ NAV ═══ */
function Nav(props) {
  var ph = props.ph;
  var mx = props.mx;
  var go = props.go;
  var rc = props.rc;
  return React.createElement('div', { style: { display: 'flex', gap: 8, justifyContent: 'center', marginTop: 24 } },
    ph > 0 ? React.createElement('button', { className: 'btn btn-sec', onClick: function() { go(ph - 1); rc(); } }, 'Back') : null,
    ph < 5 && ph < mx ? React.createElement('button', { className: 'btn btn-pri', onClick: function() { go(ph + 1); } }, 'Next Phase') : null,
    ph < 5 && ph >= mx ? React.createElement('button', { className: 'btn btn-pri', style: { opacity: .4, cursor: 'not-allowed' }, disabled: true }, 'No data for next phase') : null
  );
}

/* ═══ STYLES ═══ */
var STYLES = [
  "@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Manrope:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');",
  ":root{--ff:'Manrope',system-ui,sans-serif;--fs:'Instrument Serif',Georgia,serif;--fm:'JetBrains Mono',monospace;--bg:#fafaf9;--card:#fff;--bd:#e7e5e4;--ink:#1c1917;--t2:#57534e;--t3:#a8a29e;--accent:#1d4ed8}",
  "*{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg)}",
  ".root{min-height:100vh;background:var(--bg);font-family:var(--ff);color:var(--ink);-webkit-font-smoothing:antialiased}",
  "@keyframes enter{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}",
  "@keyframes slideIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}",
  "@keyframes glow{0%,100%{border-color:rgba(29,78,216,.15)}50%{border-color:rgba(29,78,216,.5)}}",
  "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
  "@keyframes scoreReveal{from{transform:scale(.85);opacity:0}to{transform:scale(1);opacity:1}}",
  /* Landing page animations */
  "@keyframes heroFadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}",
  "@keyframes heroPulse{0%,100%{box-shadow:0 0 0 0 rgba(29,78,216,0)}50%{box-shadow:0 0 40px 4px rgba(29,78,216,.08)}}",
  "@keyframes orbFloat1{0%,100%{transform:translate(0,0) scale(1)}25%{transform:translate(30px,-20px) scale(1.05)}50%{transform:translate(-10px,-35px) scale(.97)}75%{transform:translate(-25px,10px) scale(1.02)}}",
  "@keyframes orbFloat2{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(-40px,20px) scale(1.04)}66%{transform:translate(20px,-30px) scale(.96)}}",
  "@keyframes orbFloat3{0%,100%{transform:translate(0,0)}50%{transform:translate(15px,25px)}}",
  "@keyframes gridPulse{0%,100%{opacity:.03}50%{opacity:.06}}",
  "@keyframes statCount{from{opacity:0;transform:translateY(8px) scale(.95)}to{opacity:1;transform:translateY(0) scale(1)}}",
  "@keyframes inputGlow{0%,100%{border-color:var(--bd);box-shadow:0 2px 12px rgba(0,0,0,.03)}50%{border-color:rgba(29,78,216,.25);box-shadow:0 2px 24px rgba(29,78,216,.06)}}",
  "@keyframes moleculeRotate{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}",
  ".ani{animation:enter .45s cubic-bezier(.22,1,.36,1) both}",
  ".caret{animation:blink .65s step-end infinite;color:var(--accent)}",
  ".card{background:var(--card);border-radius:16px;border:1px solid var(--bd);transition:box-shadow .3s}",
  ".card:hover{box-shadow:0 8px 30px rgba(0,0,0,.04)}",
  ".chip{display:inline-flex;align-items:center;padding:3px 10px;border-radius:99px;font-size:10px;font-weight:600;white-space:nowrap}",
  ".bar-bg{height:4px;background:#f1f0ee;border-radius:99px;overflow:hidden}",
  ".bar-fill{height:100%;border-radius:99px;transition:width 1s cubic-bezier(.22,1,.36,1)}",
  ".btn{height:44px;padding:0 28px;border-radius:12px;font-family:var(--ff);font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;border:none}",
  ".btn-pri{background:var(--ink);color:#fff}.btn-pri:hover{background:#292524;box-shadow:0 4px 16px rgba(0,0,0,.12);transform:translateY(-1px)}",
  ".btn-sec{background:#fff;color:var(--t2);border:1px solid var(--bd)}",
  ".btn-gold{background:#1c1917;color:#fbbf24;border:2px solid #fbbf24}.btn-gold:hover{background:#292524;transform:translateY(-1px)}",
  ".btn-reset{background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;height:52px;padding:0 40px;font-size:16px;border-radius:14px;border:none;font-family:var(--ff);font-weight:700;cursor:pointer;transition:all .25s}",
  ".btn-reset:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(29,78,216,.2)}",
  ".tabs{display:flex;gap:2px;background:#f5f5f4;border-radius:14px;padding:3px}",
  ".tab{flex:1;padding:10px 8px;border-radius:11px;border:none;cursor:pointer;font-family:var(--ff);font-weight:600;font-size:11.5px;transition:all .2s;background:transparent;color:var(--t3)}",
  ".tab.on{background:#fff;color:var(--ink);box-shadow:0 1px 4px rgba(0,0,0,.05)}",
  ".step{height:28px;padding:0 11px;border-radius:7px;border:none;font-size:10px;font-weight:600;font-family:var(--ff);cursor:pointer;transition:all .25s}",
  ".step.cur{background:var(--ink);color:#fff}.step.done{background:#e7e5e4;color:var(--ink)}.step.fut{background:transparent;color:#d6d3d1;cursor:default}",
  ".lbl{font-size:9.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px}",
  ".inp{width:100%;padding:14px 18px;border:2px solid var(--bd);border-radius:12px;font-size:18px;font-weight:700;font-family:var(--ff);outline:none;background:#fff;color:var(--ink);transition:border-color .25s}",
  ".inp:focus{border-color:var(--accent)}.inp::placeholder{color:#d6d3d1;font-weight:400}",
  /* Landing page specific */
  ".hero-wrap{position:relative;overflow:hidden;padding:80px 20px 60px;min-height:80vh;display:flex;align-items:center;justify-content:center}",
  ".hero-orbs{position:absolute;inset:0;pointer-events:none;overflow:hidden}",
  ".hero-orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.35}",
  ".hero-orb-1{width:400px;height:400px;background:radial-gradient(circle,rgba(29,78,216,.3),transparent 70%);top:-100px;right:-80px;animation:orbFloat1 20s ease-in-out infinite}",
  ".hero-orb-2{width:350px;height:350px;background:radial-gradient(circle,rgba(124,58,237,.25),transparent 70%);bottom:-80px;left:-60px;animation:orbFloat2 25s ease-in-out infinite}",
  ".hero-orb-3{width:250px;height:250px;background:radial-gradient(circle,rgba(5,150,105,.2),transparent 70%);top:40%;left:60%;animation:orbFloat3 18s ease-in-out infinite}",
  ".hero-grid{position:absolute;inset:0;background-image:radial-gradient(circle,#d6d3d1 1px,transparent 1px);background-size:32px 32px;animation:gridPulse 6s ease infinite;pointer-events:none}",
  ".hero-content{position:relative;z-index:1;text-align:center;max-width:640px}",
  ".hero-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 16px;border-radius:99px;background:rgba(29,78,216,.06);border:1px solid rgba(29,78,216,.12);font-size:10px;font-weight:700;color:var(--accent);letter-spacing:1.5px;text-transform:uppercase;animation:heroFadeUp .6s cubic-bezier(.22,1,.36,1) .1s both}",
  ".hero-title{font-family:var(--fs);font-size:clamp(36px,7vw,64px);font-weight:400;letter-spacing:-1.5px;line-height:1.05;font-style:italic;margin-top:24px;animation:heroFadeUp .6s cubic-bezier(.22,1,.36,1) .2s both}",
  ".hero-sub{color:var(--t2);font-size:clamp(14px,1.6vw,16px);line-height:1.7;margin-top:20px;max-width:480px;margin-left:auto;margin-right:auto;animation:heroFadeUp .6s cubic-bezier(.22,1,.36,1) .35s both}",
  ".hero-search{max-width:560px;margin:36px auto 0;animation:heroFadeUp .6s cubic-bezier(.22,1,.36,1) .5s both}",
  ".hero-search .card{padding:28px;animation:heroPulse 4s ease infinite 2s}",
  ".hero-stats{display:flex;justify-content:center;gap:32px;margin-top:40px;animation:heroFadeUp .6s cubic-bezier(.22,1,.36,1) .7s both}",
  ".hero-stat{text-align:center}",
  ".hero-stat-num{font-family:var(--fm);font-size:24px;font-weight:800;color:var(--ink);letter-spacing:-1px}",
  ".hero-stat-label{font-size:10px;font-weight:600;color:var(--t3);letter-spacing:.5px;margin-top:2px}",
  ".hero-molecule{position:absolute;pointer-events:none;opacity:.06}",
  ".hero-molecule svg{animation:moleculeRotate 60s linear infinite}",
  ".inp-hero{animation:inputGlow 4s ease infinite 3s}",
  ".kg-item{animation:slideIn .4s cubic-bezier(.22,1,.36,1) both}",
  ".trial-item{animation:enter .4s cubic-bezier(.22,1,.36,1) both}",
  "::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:#d6d3d1;border-radius:99px}"
].join('\n');

/* ═══ MAIN APP ═══ */
function AppInner() {
  var manifestHook = useManifest();
  var manifest = manifestHook.manifest;
  var mLoad = manifestHook.loading;

  var diseaseState = useState(null);
  var diseaseId = diseaseState[0]; var setDiseaseId = diseaseState[1];
  var dataHook = useDiseaseData(diseaseId);
  var data = dataHook.data; var dLoad = dataHook.loading;

  var phState = useState(0);
  var ph = phState[0]; var setPh = phState[1];
  var inpState = useState('');
  var inp = inpState[0]; var setInp = inpState[1];
  var busyState = useState(false);
  var busy = busyState[0]; var setBusy = busyState[1];
  var matchState = useState(null);
  var matchResult = matchState[0]; var setMatchResult = matchState[1];
  var tabState = useState('faers');
  var tab = tabState[0]; var setTab = tabState[1];
  var courtState = useState(false);
  var courtOn = courtState[0]; var setCourtOn = courtState[1];
  var judgeState = useState(false);
  var judgeOn = judgeState[0]; var setJudgeOn = judgeState[1];
  var expandState = useState({});
  var expanded = expandState[0]; var setExpanded = expandState[1];
  var toggleExpand = useCallback(function(key) { setExpanded(function(prev) { var n = {}; for (var k in prev) n[k] = prev[k]; n[key] = !prev[key]; return n; }); }, []);
  var secState = useState(0);
  var sec = secState[0]; var setSec = secState[1];
  var logoState = useState(null);
  var logoUrl = logoState[0]; var setLogoUrl = logoState[1];
  var tmr = useRef(null);
  var autoStarted = useRef(false);
  var typingIv = useRef(null);

  useEffect(function() {
    ['png','jpg','jpeg','svg','webp'].forEach(function(ext) {
      fetch('/logo.' + ext, { method: 'HEAD' }).then(function(r) { if (r.ok) setLogoUrl('/logo.' + ext); }).catch(function() {});
    });
  }, []);

  var fullReset = useCallback(function() {
    setPh(0); setInp(''); setBusy(false); setMatchResult(null);
    setTab('faers'); setCourtOn(false); setJudgeOn(false); setSec(0);
    setDiseaseId(null); autoStarted.current = false;
    if (typingIv.current) { clearInterval(typingIv.current); typingIv.current = null; }
    if (tmr.current) { clearInterval(tmr.current); tmr.current = null; }
  }, []);

  var handleSubmit = useCallback(function() {
    if (!inp.trim() || !manifest) return;
    var match = fuzzyMatch(inp, manifest.diseases);
    if (match) {
      // Reset state for fresh load
      setPh(0); setBusy(false); setTab('faers'); setCourtOn(false); setJudgeOn(false); setExpanded({});
      if (typingIv.current) { clearInterval(typingIv.current); typingIv.current = null; }
      autoStarted.current = false;
      setMatchResult({ found: true, disease: match });
      setDiseaseId(match.id);
    } else {
      setMatchResult({ found: false });
    }
  }, [inp, manifest]);

  useEffect(function() {
    if (!matchResult || !matchResult.found || !data || autoStarted.current) return;
    if (ph !== 0) return;
    // Only proceed if the loaded data matches the selected disease
    if (data.disease !== matchResult.disease.id) return;
    autoStarted.current = true;
    setBusy(true);
    var name = matchResult.disease.label || data.diseaseLabel || data.disease || '';
    setInp('');
    var i = 0;
    if (typingIv.current) clearInterval(typingIv.current);
    typingIv.current = setInterval(function() {
      if (i <= name.length) { setInp(name.slice(0, i)); i++; }
      else { clearInterval(typingIv.current); typingIv.current = null; setTimeout(function() { setBusy(false); setPh(1); }, 500); }
    }, 55);
  }, [matchResult, data]);

  useEffect(function() {
    if (ph >= 1 && !tmr.current) {
      var t0 = Date.now();
      tmr.current = setInterval(function() { setSec((Date.now() - t0) / 1000); }, 80);
    }
    if (ph === 5 && tmr.current) { clearInterval(tmr.current); tmr.current = null; }
  }, [ph]);

  useEffect(function() {
    if (ph === 4) { var t = setTimeout(function() { setCourtOn(true); }, 400); return function() { clearTimeout(t); }; }
  }, [ph]);

  var PH = ['Input', 'Knowledge Graph', 'Trial Scanner', 'Evidence', 'Court', 'Verdict'];
  var diseases = (manifest && manifest.diseases) ? manifest.diseases : [];
  var maxPh = data ? 5 : 0;
  var resetCourt = function() { setCourtOn(false); setJudgeOn(false); };

  var kgList = (data && data.kgList) ? data.kgList : [];
  var trials = ((data && data.trials) ? data.trials : []).slice(0, 5);
  var totalTrials = (data && data.trials) ? data.trials.length : 0;
  var verdicts = (data && data.verdicts) ? data.verdicts : [];
  var evidence = (data && data.evidence) ? data.evidence : [];
  var debate = (data && data.debate) ? data.debate : [];
  var faers = data ? data.faers : null;
  var tiers = (data && data.tiers) ? data.tiers : {};

  /* ─── RENDER ─── */
  return React.createElement('div', { className: 'root' },
    React.createElement('style', null, STYLES),

    /* HEADER */
    React.createElement('header', { style: { background: 'rgba(250,250,249,.92)', backdropFilter: 'blur(16px)', borderBottom: '1px solid var(--bd)', padding: '0 24px', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 999 } },
      React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } },
        logoUrl
          ? React.createElement('img', { src: logoUrl, alt: 'RescueRx', style: { height: 30, width: 'auto', borderRadius: 6 } })
          : React.createElement('div', { style: { width: 28, height: 28, borderRadius: 7, background: 'var(--ink)', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 11, fontWeight: 900 } }, 'Rx'),
        React.createElement('span', { style: { fontSize: 16, fontWeight: 800, letterSpacing: -.5 } }, 'Rescue', React.createElement('span', { style: { color: 'var(--accent)' } }, 'Rx')),
        React.createElement('span', { style: { fontSize: 9, color: 'var(--t3)', fontWeight: 600, letterSpacing: .5 } }, 'TreeHacks 2026')
      ),
      data && ph > 0 ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 2 } },
        PH.map(function(l, i) {
          return React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center' } },
            React.createElement('button', {
              className: 'step ' + (ph === i ? 'cur' : i < ph ? 'done' : 'fut'),
              disabled: i > ph || i > maxPh,
              onClick: function() { if (i <= ph) { setPh(i); resetCourt(); } }
            }, l),
            i < PH.length - 1 ? React.createElement('div', { style: { width: 10, height: 1.5, background: i < ph ? '#a8a29e' : '#e7e5e4', margin: '0 1px' } }) : null
          );
        })
      ) : null,
      ph >= 1 ? React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 12, fontWeight: 600, color: ph === 5 ? '#059669' : 'var(--accent)', minWidth: 54, textAlign: 'right' } }, ph === 5 ? 'Done' : sec.toFixed(1) + 's') : null
    ),

    /* MAIN */
    React.createElement('main', { style: { maxWidth: 1040, margin: '0 auto', padding: '28px 20px 100px' } },

      mLoad ? React.createElement('div', { style: { textAlign: 'center', paddingTop: 120, fontSize: 16, color: 'var(--t3)', fontWeight: 600 } }, 'Loading...') : null,

      /* PHASE 0: INPUT — stunning hero */
      !mLoad && ph === 0 && !busy ? React.createElement('div', { className: 'hero-wrap' },
        /* Background effects */
        React.createElement('div', { className: 'hero-orbs' },
          React.createElement('div', { className: 'hero-orb hero-orb-1' }),
          React.createElement('div', { className: 'hero-orb hero-orb-2' }),
          React.createElement('div', { className: 'hero-orb hero-orb-3' }),
          React.createElement('div', { className: 'hero-grid' })
        ),
        /* Floating molecule decorations */
        React.createElement('div', { className: 'hero-molecule', style: { top: '15%', left: '8%' } },
          React.createElement('svg', { width: 80, height: 80, viewBox: '0 0 80 80' },
            React.createElement('circle', { cx: 20, cy: 20, r: 4, fill: 'currentColor' }),
            React.createElement('circle', { cx: 55, cy: 15, r: 3, fill: 'currentColor' }),
            React.createElement('circle', { cx: 40, cy: 50, r: 5, fill: 'currentColor' }),
            React.createElement('circle', { cx: 65, cy: 55, r: 3.5, fill: 'currentColor' }),
            React.createElement('line', { x1: 20, y1: 20, x2: 55, y2: 15, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 20, y1: 20, x2: 40, y2: 50, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 55, y1: 15, x2: 65, y2: 55, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 40, y1: 50, x2: 65, y2: 55, stroke: 'currentColor', strokeWidth: 1.5 })
          )
        ),
        React.createElement('div', { className: 'hero-molecule', style: { bottom: '20%', right: '10%', transform: 'rotate(45deg)' } },
          React.createElement('svg', { width: 100, height: 100, viewBox: '0 0 100 100' },
            React.createElement('circle', { cx: 50, cy: 20, r: 5, fill: 'currentColor' }),
            React.createElement('circle', { cx: 25, cy: 50, r: 4, fill: 'currentColor' }),
            React.createElement('circle', { cx: 75, cy: 50, r: 4, fill: 'currentColor' }),
            React.createElement('circle', { cx: 50, cy: 80, r: 3.5, fill: 'currentColor' }),
            React.createElement('circle', { cx: 15, cy: 80, r: 3, fill: 'currentColor' }),
            React.createElement('line', { x1: 50, y1: 20, x2: 25, y2: 50, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 50, y1: 20, x2: 75, y2: 50, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 25, y1: 50, x2: 50, y2: 80, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 25, y1: 50, x2: 15, y2: 80, stroke: 'currentColor', strokeWidth: 1.5 }),
            React.createElement('line', { x1: 75, y1: 50, x2: 50, y2: 80, stroke: 'currentColor', strokeWidth: 1.5 })
          )
        ),
        /* Content */
        React.createElement('div', { className: 'hero-content' },
          React.createElement('div', { className: 'hero-badge' },
            React.createElement('span', { style: { width: 6, height: 6, borderRadius: '50%', background: '#059669', animation: 'blink 1.5s ease infinite' } }),
            'Multi-Agent Drug Repurposing'
          ),
          React.createElement('h1', { className: 'hero-title' },
            'Rescue abandoned drugs.', React.createElement('br'),
            React.createElement('span', { style: { color: 'var(--accent)', fontStyle: 'normal', fontWeight: 600 } }, 'In 60 seconds.')
          ),
          React.createElement('p', { className: 'hero-sub' },
            'Nine AI agents scan clinical trials, knowledge graphs, FDA reports, and literature \u2014 then ', React.createElement('strong', null, 'debate the evidence'), ' in an adversarial court.'
          ),
          React.createElement('div', { className: 'hero-search' },
            React.createElement('div', { className: 'card', style: { padding: 28 } },
              React.createElement('div', { className: 'lbl' }, 'Enter a disease'),
              React.createElement('form', { onSubmit: function(e) { e.preventDefault(); handleSubmit(); }, style: { display: 'flex', gap: 10 } },
                React.createElement('input', { className: 'inp inp-hero', value: inp, onChange: function(e) { setInp(e.target.value); setMatchResult(null); }, placeholder: 'Type a disease name...', autoFocus: true, disabled: dLoad }),
                React.createElement('button', { type: 'submit', className: 'btn btn-pri', disabled: !inp.trim() || dLoad, style: { opacity: !inp.trim() ? .5 : 1, flexShrink: 0 } }, dLoad ? 'Loading...' : 'Analyze')
              ),
              matchResult && !matchResult.found ? React.createElement('div', { style: { marginTop: 12, padding: '10px 14px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', fontSize: 12, color: '#991b1b' } }, 'No data for "' + inp + '". Available: ' + diseases.map(function(d) { return d.label; }).join(', ')) : null
            )
          ),
          React.createElement('div', { className: 'hero-stats' },
            React.createElement('div', { className: 'hero-stat' },
              React.createElement('div', { className: 'hero-stat-num' }, '9'),
              React.createElement('div', { className: 'hero-stat-label' }, 'AI Agents')
            ),
            React.createElement('div', { style: { width: 1, height: 32, background: 'var(--bd)', alignSelf: 'center' } }),
            React.createElement('div', { className: 'hero-stat' },
              React.createElement('div', { className: 'hero-stat-num' }, '20M+'),
              React.createElement('div', { className: 'hero-stat-label' }, 'FAERS Reports')
            ),
            React.createElement('div', { style: { width: 1, height: 32, background: 'var(--bd)', alignSelf: 'center' } }),
            React.createElement('div', { className: 'hero-stat' },
              React.createElement('div', { className: 'hero-stat-num' }, '24K+'),
              React.createElement('div', { className: 'hero-stat-label' }, 'Compounds Scored')
            ),
            React.createElement('div', { style: { width: 1, height: 32, background: 'var(--bd)', alignSelf: 'center' } }),
            React.createElement('div', { className: 'hero-stat' },
              React.createElement('div', { className: 'hero-stat-num' }, '3'),
              React.createElement('div', { className: 'hero-stat-label' }, 'Adversarial Layers')
            )
          )
        )
      ) : null,

      /* TYPING ANIMATION */
      busy && ph === 0 ? React.createElement('div', { className: 'ani', style: { textAlign: 'center', paddingTop: 120 } },
        React.createElement('div', { style: { fontSize: 11, fontWeight: 700, color: 'var(--t3)', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 16 } }, 'Analyzing'),
        React.createElement('div', { style: { fontSize: 36, fontWeight: 800, fontFamily: 'var(--fm)', color: 'var(--accent)', border: '2px solid var(--accent)', borderRadius: 14, padding: '16px 24px', display: 'inline-block', animation: 'glow 1.2s ease infinite' } }, inp, React.createElement('span', { className: 'caret' }, '|'))
      ) : null,

      /* PHASE 1: KG */
      data && ph === 1 ? React.createElement('div', { className: 'ani' },
        React.createElement(SH, { n: '01', t: 'Knowledge Graph Scoring', s: 'RotatE embeddings \u00B7 ' + ((data.meta && data.meta.total_scored) || 0).toLocaleString() + ' compounds \u00B7 ' + ((data.meta && data.meta.timing_ms) || 0) + 'ms' }),
        React.createElement('div', { className: 'card', style: { padding: 20, marginTop: 20 } },
          React.createElement('div', { className: 'lbl' }, 'Top Ranked \u2014 Percentile vs. ' + (data.diseaseLabel || '')),
          kgList.length === 0 ? React.createElement('div', { style: { padding: 20, textAlign: 'center', color: 'var(--t3)' } }, 'No KG data') : null,
          React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 } },
            kgList.map(function(dr, i) {
              var drop = dr.status === 'dropped';
              return React.createElement('div', { key: dr.rank + '-' + dr.name, className: 'kg-item', style: { animationDelay: (i * 0.15) + 's', padding: '10px 14px', borderRadius: 10, background: drop ? '#eff6ff' : '#fafaf9', border: drop ? '1.5px solid #93c5fd' : '1px solid #f1f0ee' } },
                React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 } },
                  React.createElement('span', { style: { display: 'flex', alignItems: 'center', gap: 6 } },
                    React.createElement('span', { style: { fontWeight: 700, fontSize: 12.5 } }, dr.name),
                    drop ? React.createElement('span', { className: 'chip', style: { background: '#dbeafe', color: '#1e40af', fontSize: 8, padding: '1px 6px' } }, 'DROPPED') : null
                  ),
                  React.createElement('span', { style: { fontFamily: 'var(--fm)', fontSize: 13, fontWeight: 700, color: drop ? '#2563eb' : '#059669' } },
                    React.createElement(CountUp, { to: dr.pct, d: 2, s: '%' })
                  )
                ),
                React.createElement(Bar, { pct: dr.pct, color: drop ? '#3b82f6' : '#a8a29e', delay: i * 150 }),
                React.createElement('div', { style: { fontSize: 9.5, color: 'var(--t3)', marginTop: 3 } }, 'z: ' + (dr.z || 0).toFixed(3))
              );
            })
          )
        ),
        React.createElement(Nav, { ph: ph, mx: maxPh, go: setPh, rc: resetCourt })
      ) : null,

      /* PHASE 2: TRIALS */
      data && ph === 2 ? React.createElement('div', { className: 'ani' },
        React.createElement(SH, { n: '02', t: 'Clinical Trial Scanner', s: 'Top ' + trials.length + ' of ' + totalTrials + ' results' }),
        React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 8, marginTop: 20 } },
          trials.length === 0 ? React.createElement('div', { style: { padding: 20, textAlign: 'center', color: 'var(--t3)' } }, 'No trial data available for this disease.') : null,
          trials.map(function(tr, i) {
            var gold = tr.isPrime;
            var active = tr.st === 'Active' || (tr.tag || '').indexOf('ONGOING') >= 0;
            return React.createElement('div', { key: (tr.nct || '') + '-' + i, className: 'trial-item card', style: { animationDelay: (i * 0.12) + 's', padding: '14px 18px', display: 'grid', gridTemplateColumns: '1fr auto', gap: 14, alignItems: 'center', borderLeft: '3px solid ' + (gold ? '#f59e0b' : active ? '#059669' : '#a8a29e'), background: gold ? '#fffbeb' : 'var(--card)' } },
              React.createElement('div', null,
                React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 } },
                  React.createElement('span', { style: { fontWeight: 700, fontSize: 14 } }, tr.drug),
                  React.createElement('span', { className: 'chip', style: { background: '#f5f5f4', color: 'var(--t2)' } }, tr.ph),
                  React.createElement('span', { className: 'chip', style: { background: tr.st === 'Terminated' ? '#fef3c7' : '#d1fae5', color: tr.st === 'Terminated' ? '#92400e' : '#065f46' } }, tr.st)
                ),
                React.createElement('div', { style: { fontSize: 11, color: 'var(--t3)' } }, tr.nct),
                React.createElement('div', { style: { fontSize: 11, color: 'var(--t2)', marginTop: 2, fontStyle: 'italic' } }, '"' + tr.why + '"')
              ),
              React.createElement('span', { style: { background: gold ? '#fef3c7' : active ? '#d1fae5' : '#f5f5f4', color: gold ? '#92400e' : active ? '#065f46' : '#991b1b', padding: '5px 12px', borderRadius: 7, fontSize: 10, fontWeight: 700 } }, tr.tag)
            );
          })
        ),
        React.createElement(Nav, { ph: ph, mx: maxPh, go: setPh, rc: resetCourt })
      ) : null,

      /* PHASE 3: EVIDENCE */
      data && ph === 3 ? React.createElement('div', { className: 'ani' },
        React.createElement(SH, { n: '03', t: 'Evidence Wall', s: ((data.meta && data.meta.total_citations) || 0) + ' citations across ' + evidence.length + ' drugs' }),
        React.createElement('div', { className: 'tabs', style: { marginTop: 20 } },
          [['faers','FAERS'],['lit','Literature'],['mol','Molecular'],['tiers','Tiers']].map(function(pair) {
            return React.createElement('button', { key: pair[0], className: 'tab ' + (tab === pair[0] ? 'on' : ''), onClick: function() { setTab(pair[0]); } }, pair[1]);
          })
        ),
        React.createElement('div', { className: 'card', style: { marginTop: 8, padding: 24, minHeight: 260 } },
          tab === 'faers' ? React.createElement('div', { className: 'ani' },
            React.createElement('div', { className: 'lbl' }, 'FDA Adverse Events' + (faers ? ' \u2014 ' + (faers.total_reports || 0).toLocaleString() + ' Reports Screened' : '')),
            !faers ? React.createElement('div', { style: { color: 'var(--t3)', fontSize: 13 } }, 'No FAERS data available for this disease.') : null,
            faers && faers.summary ? React.createElement('div', { style: { background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: 14, marginBottom: 14, fontSize: 12.5, color: '#78350f', lineHeight: 1.6 } }, faers.summary) : null,
            faers ? (faers.drugs || []).map(function(d, i) {
              var hasRor = d.ror != null && d.ror > 0;
              var isRisk = hasRor && d.ror > 1.5;
              var isProtective = hasRor && d.ror < 0.5;
              return React.createElement('div', { key: (d.name || '') + i, style: { padding: '12px 14px', borderRadius: 10, background: isRisk ? '#fef2f2' : isProtective ? '#f0fdf4' : '#fafaf9', border: '1px solid ' + (isRisk ? '#fecaca' : isProtective ? '#bbf7d0' : '#f1f0ee'), marginBottom: 6 } },
                React.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: d.interp ? 4 : 0 } },
                  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
                    React.createElement('span', { style: { fontWeight: 700, fontSize: 13 } }, d.name),
                    React.createElement('span', { style: { fontSize: 10, color: 'var(--t3)' } }, d.coReports + ' co-reports'),
                    hasRor ? React.createElement('span', { style: { fontFamily: 'var(--fm)', fontSize: 10, fontWeight: 700, color: isRisk ? '#dc2626' : isProtective ? '#059669' : '#d97706' } }, 'ROR=' + d.ror.toFixed(2)) : null
                  ),
                  React.createElement('span', { className: 'chip', style: { background: isRisk ? '#fee2e2' : isProtective ? '#d1fae5' : d.hasSignal ? '#fef3c7' : '#f5f5f4', color: isRisk ? '#991b1b' : isProtective ? '#065f46' : d.hasSignal ? '#92400e' : 'var(--t3)' } }, isRisk ? 'RISK' : isProtective ? 'PROTECTIVE' : d.coReports === 0 ? 'NO DATA' : d.hasSignal ? 'SIGNAL' : 'NEUTRAL')
                ),
                d.interp ? React.createElement('div', { style: { fontSize: 11, color: 'var(--t2)', lineHeight: 1.5, marginTop: 2 } }, d.interp) : null
              );
            }) : null
          ) : null,
          tab === 'lit' ? React.createElement('div', { className: 'ani' },
            React.createElement('div', { className: 'lbl' }, 'Literature Review'),
            evidence.filter(function(e) { return e.literature && (e.literature.evidence_level || e.literature.mechanism || (e.literature.citation_count || 0) > 0 || (e.literature.clinical_entries && e.literature.clinical_entries.length)); }).length === 0 ? React.createElement('div', { style: { color: 'var(--t3)', fontSize: 13 } }, 'No literature data available.') : null,
            evidence.filter(function(e) { return e.literature && (e.literature.evidence_level || e.literature.mechanism || (e.literature.citation_count || 0) > 0 || (e.literature.clinical_entries && e.literature.clinical_entries.length)); }).map(function(e, i) {
              var lit = e.literature || {};
              var level = lit.evidence_level || '';
              var isStrong = level === 'STRONG' || level === 'PURSUE';
              var isMod = level === 'MODERATE' || level === 'INVESTIGATE_FURTHER';
              var litKey = 'lit-' + (e.name || i);
              var isOpen = expanded[litKey];
              return React.createElement('div', { key: (e.name || '') + i, style: { borderRadius: 12, background: '#fafaf9', border: '1px solid ' + (isOpen ? (isStrong ? '#86efac' : isMod ? '#fde68a' : '#e7e5e4') : '#f1f0ee'), marginBottom: 8, overflow: 'hidden', transition: 'border-color .2s' } },
                /* Clickable Header */
                React.createElement('div', { onClick: function() { toggleExpand(litKey); }, style: { padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', userSelect: 'none' } },
                  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
                    React.createElement('span', { style: { fontWeight: 800, fontSize: 15 } }, e.name),
                    React.createElement('span', { className: 'chip', style: { background: isStrong ? '#d1fae5' : isMod ? '#fef3c7' : '#f5f5f4', color: isStrong ? '#065f46' : isMod ? '#92400e' : 'var(--t3)' } }, (lit.citation_count || 0) + ' citations'),
                    level ? React.createElement('span', { className: 'chip', style: { background: isStrong ? '#d1fae5' : isMod ? '#fef3c7' : '#fee2e2', color: isStrong ? '#065f46' : isMod ? '#92400e' : '#991b1b' } }, level.replace(/_/g, ' ')) : null,
                    lit.recommendation ? React.createElement('span', { className: 'chip', style: { background: '#eff6ff', color: '#1e40af' } }, lit.recommendation.replace(/_/g, ' ')) : null
                  ),
                  React.createElement('span', { style: { fontSize: 16, color: 'var(--t3)', transition: 'transform .2s', transform: isOpen ? 'rotate(180deg)' : 'rotate(0)', flexShrink: 0, marginLeft: 8 } }, '\u25BE')
                ),
                /* Expandable Content */
                isOpen ? React.createElement('div', { style: { padding: '0 18px 16px', animation: 'enter .25s ease both' } },
                  lit.mechanism ? React.createElement('div', { style: { fontSize: 12, color: 'var(--t2)', lineHeight: 1.6, marginBottom: 10 } }, lit.mechanism) : null,
                  lit.clinical_entries && lit.clinical_entries.length ? React.createElement('div', { style: { marginBottom: 10 } },
                    React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: 'var(--t3)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 } }, 'Clinical Evidence'),
                    lit.clinical_entries.map(function(ce, ci) {
                      return React.createElement('div', { key: ci, style: { fontSize: 11.5, color: 'var(--t2)', lineHeight: 1.55, marginBottom: 6, paddingLeft: 10, borderLeft: '2px solid #e7e5e4' } },
                        React.createElement('span', { style: { fontWeight: 700, fontSize: 10, color: 'var(--t3)' } }, ce.label + ': '),
                        ce.text
                      );
                    })
                  ) : null,
                  lit.safety ? React.createElement('div', { style: { fontSize: 11.5, color: '#78350f', lineHeight: 1.55, padding: '8px 10px', borderRadius: 8, background: '#fffbeb', marginBottom: 6 } },
                    React.createElement('span', { style: { fontWeight: 700, fontSize: 10 } }, 'SAFETY: '), lit.safety
                  ) : null,
                  lit.regulatory ? React.createElement('div', { style: { fontSize: 11.5, color: '#1e40af', lineHeight: 1.55, padding: '8px 10px', borderRadius: 8, background: '#eff6ff', marginBottom: 6 } },
                    React.createElement('span', { style: { fontWeight: 700, fontSize: 10 } }, 'REGULATORY: '), lit.regulatory
                  ) : null,
                  (e.strengths && e.strengths.length) || (e.weaknesses && e.weaknesses.length) ? React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 } },
                    e.strengths && e.strengths.length ? React.createElement('div', null,
                      React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#059669', letterSpacing: 1, marginBottom: 3 } }, 'STRENGTHS'),
                      e.strengths.slice(0, 4).map(function(s, si) {
                        return React.createElement('div', { key: si, style: { fontSize: 10.5, color: 'var(--t2)', lineHeight: 1.5, marginBottom: 2 } }, '\u2713 ' + s);
                      })
                    ) : null,
                    e.weaknesses && e.weaknesses.length ? React.createElement('div', null,
                      React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#dc2626', letterSpacing: 1, marginBottom: 3 } }, 'WEAKNESSES'),
                      e.weaknesses.slice(0, 4).map(function(w, wi) {
                        return React.createElement('div', { key: wi, style: { fontSize: 10.5, color: 'var(--t2)', lineHeight: 1.5, marginBottom: 2 } }, '\u2717 ' + w);
                      })
                    ) : null
                  ) : null
                ) : null
              );
            })
          ) : null,
          tab === 'mol' ? React.createElement('div', { className: 'ani' },
            React.createElement('div', { className: 'lbl' }, 'Molecular Similarity Analysis'),
            evidence.filter(function(e) { return e.molecular && (e.molecular.max_tanimoto_approved != null || (e.molecular.database_hits && e.molecular.database_hits.length) || e.molecular.class); }).length === 0 ? React.createElement('div', { style: { color: 'var(--t3)', fontSize: 13 } }, 'No molecular data available.') : null,
            evidence.filter(function(e) { return e.molecular && (e.molecular.max_tanimoto_approved != null || (e.molecular.database_hits && e.molecular.database_hits.length) || e.molecular.class); }).map(function(e, i) {
              var mol = e.molecular || {};
              var molKey = 'mol-' + (e.name || i);
              var isOpen = expanded[molKey];
              var tc = mol.max_tanimoto_approved != null ? (mol.max_tanimoto_approved >= 0.7 ? '#059669' : mol.max_tanimoto_approved >= 0.4 ? '#d97706' : '#dc2626') : 'var(--t3)';
              return React.createElement('div', { key: (e.name || '') + i, style: { borderRadius: 12, background: '#fafaf9', border: '1px solid ' + (isOpen ? '#e7e5e4' : '#f1f0ee'), marginBottom: 8, overflow: 'hidden', transition: 'border-color .2s' } },
                /* Clickable Header */
                React.createElement('div', { onClick: function() { toggleExpand(molKey); }, style: { padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', userSelect: 'none' } },
                  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
                    React.createElement('span', { style: { fontWeight: 800, fontSize: 15 } }, e.name),
                    mol.structurally_novel ? React.createElement('span', { className: 'chip', style: { background: '#eff6ff', color: '#1e40af' } }, 'Novel') : null,
                    mol.most_similar ? React.createElement('span', { className: 'chip', style: { background: '#f5f5f4', color: 'var(--t2)' } }, '\u2248 ' + mol.most_similar) : null
                  ),
                  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
                    mol.max_tanimoto_approved != null ? React.createElement('span', { style: { fontFamily: 'var(--fm)', fontSize: 16, fontWeight: 700, color: tc } }, mol.max_tanimoto_approved.toFixed(3)) : null,
                    React.createElement('span', { style: { fontSize: 16, color: 'var(--t3)', transition: 'transform .2s', transform: isOpen ? 'rotate(180deg)' : 'rotate(0)' } }, '\u25BE')
                  )
                ),
                /* Expandable Content */
                isOpen ? React.createElement('div', { style: { padding: '0 18px 16px', animation: 'enter .25s ease both' } },
                  mol.smiles ? React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 10, color: 'var(--t3)', padding: '6px 10px', borderRadius: 8, background: '#f5f5f4', marginBottom: 8, wordBreak: 'break-all' } }, mol.smiles) : null,
                  mol.class ? React.createElement('div', { style: { fontSize: 11.5, color: 'var(--t2)', lineHeight: 1.55, marginBottom: 10 } }, mol.class) : null,
                  mol.database_hits && mol.database_hits.length ? React.createElement('div', { style: { marginBottom: 8 } },
                    React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: 'var(--t3)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 } }, 'Similarity (Tanimoto)'),
                    mol.database_hits.map(function(h, hi) {
                      var hc = h.tanimoto >= 0.7 ? '#059669' : h.tanimoto >= 0.4 ? '#d97706' : '#a8a29e';
                      return React.createElement('div', { key: hi, style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #f1f0ee', marginBottom: 3 } },
                        React.createElement('div', null,
                          React.createElement('span', { style: { fontWeight: 600, fontSize: 12 } }, h.name),
                          h.interp ? React.createElement('span', { style: { fontSize: 10, color: 'var(--t3)', marginLeft: 8 } }, h.interp) : null
                        ),
                        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6 } },
                          React.createElement('div', { style: { width: 40, height: 4, borderRadius: 2, background: '#f1f0ee', overflow: 'hidden' } },
                            React.createElement('div', { style: { width: (h.tanimoto * 100) + '%', height: '100%', borderRadius: 2, background: hc } })
                          ),
                          React.createElement('span', { style: { fontFamily: 'var(--fm)', fontSize: 11, fontWeight: 700, color: hc, minWidth: 36, textAlign: 'right' } }, h.tanimoto.toFixed(2))
                        )
                      );
                    })
                  ) : null,
                  /* Advantages + Disadvantages */
                  (mol.advantages && mol.advantages.length) || (mol.disadvantages && mol.disadvantages.length) ? React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 } },
                    mol.advantages && mol.advantages.length ? React.createElement('div', null,
                      React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#059669', letterSpacing: 1, marginBottom: 3 } }, 'ADVANTAGES'),
                      mol.advantages.map(function(a, ai) {
                        return React.createElement('div', { key: ai, style: { fontSize: 10.5, color: 'var(--t2)', lineHeight: 1.5, marginBottom: 2 } }, '\u2713 ' + a);
                      })
                    ) : null,
                    mol.disadvantages && mol.disadvantages.length ? React.createElement('div', null,
                      React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#dc2626', letterSpacing: 1, marginBottom: 3 } }, 'DISADVANTAGES'),
                      mol.disadvantages.map(function(d, di) {
                        return React.createElement('div', { key: di, style: { fontSize: 10.5, color: 'var(--t2)', lineHeight: 1.5, marginBottom: 2 } }, '\u2717 ' + d);
                      })
                    ) : null
                  ) : null
                ) : null
              );
            })
          ) : null,
          tab === 'tiers' ? React.createElement('div', { className: 'ani' },
            React.createElement('div', { className: 'lbl' }, 'Investigation Tiers'),
            (function() {
              var tierKeys = Object.keys(tiers).filter(function(k) { return Array.isArray(tiers[k]) && tiers[k].length > 0; });
              if (!tierKeys.length) return React.createElement('div', { style: { color: 'var(--t3)', fontSize: 13 } }, 'No tier data available.');
              // Color map by tier number or keyword
              var tierStyle = function(k) {
                var kl = k.toLowerCase();
                if (kl.includes('1') || kl.includes('prime')) return { c: '#059669', b: '#d1fae5', bc: '#86efac', label: 'TIER 1 \u2014 PURSUE' };
                if (kl.includes('2') || kl.includes('strong')) return { c: '#d97706', b: '#fef3c7', bc: '#fde68a', label: 'TIER 2 \u2014 INVESTIGATE' };
                if (kl.includes('3') || kl.includes('established') || kl.includes('moderate')) return { c: '#9ca3af', b: '#f5f5f4', bc: '#e7e5e4', label: 'TIER 3 \u2014 ESTABLISHED' };
                return { c: '#dc2626', b: '#fee2e2', bc: '#fecaca', label: 'TIER 4 \u2014 INSUFFICIENT' };
              };
              return tierKeys.map(function(k) {
                var ts = tierStyle(k);
                var dr = tiers[k];
                return React.createElement('div', { key: k, style: { padding: '14px 16px', borderRadius: 12, background: ts.b, border: '1.5px solid ' + ts.bc, marginBottom: 8 } },
                  React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 10, fontWeight: 800, color: ts.c, letterSpacing: 1, marginBottom: 6 } }, ts.label),
                  dr.map(function(d, di) {
                    return React.createElement('div', { key: di, style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,.6)', marginBottom: 4 } },
                      React.createElement('div', null,
                        React.createElement('span', { style: { fontWeight: 700, fontSize: 13 } }, d.drug_name || d.name || ''),
                        d.rescue_score ? React.createElement('span', { style: { fontFamily: 'var(--fm)', fontSize: 11, fontWeight: 700, marginLeft: 8, color: ts.c } }, d.rescue_score + '/100') : null,
                        d.rank ? React.createElement('span', { style: { fontSize: 10, color: 'var(--t3)', marginLeft: 6 } }, '#' + d.rank) : null
                      ),
                      React.createElement('div', { style: { fontSize: 10.5, color: 'var(--t2)', maxWidth: '60%', textAlign: 'right' } }, d.justification || '')
                    );
                  })
                );
              });
            })()
          ) : null
        ),
        React.createElement(Nav, { ph: ph, mx: maxPh, go: setPh, rc: resetCourt })
      ) : null,

      /* PHASE 4: COURT */
      data && ph === 4 ? React.createElement('div', { className: 'ani' },
        React.createElement(SH, { n: '04', t: 'Adversarial Court', s: (data.topDrug || '?') + ' \u2014 ' + debate.length + ' exchanges' }),
        React.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 28, margin: '12px 0 8px' } },
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6 } }, React.createElement('div', { style: { width: 10, height: 10, borderRadius: 3, background: '#059669' } }), React.createElement('span', { style: { fontSize: 11, fontWeight: 700, color: '#059669' } }, 'Advocate')),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6 } }, React.createElement('div', { style: { width: 10, height: 10, borderRadius: 3, background: '#dc2626' } }), React.createElement('span', { style: { fontSize: 11, fontWeight: 700, color: '#dc2626' } }, 'Skeptic'))
        ),
        React.createElement('div', { className: 'card', style: { padding: '18px 22px', marginTop: 8 } }, React.createElement(DebateTimeline, { debate: debate, active: courtOn })),
        !judgeOn ? React.createElement('div', { style: { textAlign: 'center', marginTop: 18 } },
          React.createElement('button', { className: 'btn btn-gold', onClick: function() { setJudgeOn(true); }, style: { fontSize: 14, padding: '0 36px' } }, 'Reveal Judge Verdict')
        ) : null,
        judgeOn ? React.createElement('div', { className: 'ani', style: { marginTop: 14, padding: 20, borderRadius: 16, background: 'linear-gradient(135deg,#fffbeb,#fef3c7)', border: '1.5px solid #fde68a' } },
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 } },
            React.createElement('div', { style: { width: 28, height: 28, borderRadius: 7, background: 'linear-gradient(135deg,#d97706,#b45309)', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 12, fontWeight: 800 } }, 'J'),
            React.createElement('span', { style: { fontWeight: 800, fontSize: 14, color: '#78350f' } }, 'JUDGE \u2014 FINAL RULING')
          ),
          React.createElement(JudgeVerdict, { points: (data && data.judgePoints) || [], topDrug: (data && data.topDrug) || '', topVerdict: data && data.topDrugVerdict, active: judgeOn })
        ) : null,
        React.createElement(Nav, { ph: ph, mx: maxPh, go: setPh, rc: resetCourt })
      ) : null,

      /* PHASE 5: VERDICT + RESET */
      data && ph === 5 ? React.createElement('div', { className: 'ani' },
        React.createElement(SH, { n: '05', t: 'Rescue Verdicts', s: (data.diseaseLabel || '') + ' \u2014 ' + verdicts.length + ' candidates evaluated' }),
        React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 14, marginTop: 20 } },
          verdicts.map(function(dr, i) {
            var s = dr.score || 0;
            var isTop = i === 0;
            var isPursue = s >= 70;
            var isInvestigate = s >= 50 && s < 70;
            return React.createElement('div', { key: (dr.name || '') + i, className: 'card', style: { padding: 0, overflow: 'hidden', animation: 'enter .5s ease ' + (i * .12) + 's both', borderColor: isTop ? '#86efac' : 'var(--bd)', borderWidth: isTop ? 2 : 1 } },
              /* Top bar with score + drug name */
              React.createElement('div', { style: { padding: '18px 22px', display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 18, alignItems: 'center' } },
                React.createElement(ScoreRing, { score: s, delay: i * 100 }),
                React.createElement('div', null,
                  React.createElement('div', { style: { display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' } },
                    React.createElement('span', { style: { fontSize: 18, fontWeight: 800 } }, dr.name),
                    React.createElement('span', { className: 'chip', style: { padding: '3px 10px', fontSize: 10, fontWeight: 700, background: isPursue ? '#d1fae5' : isInvestigate ? '#fef3c7' : '#fee2e2', color: isPursue ? '#065f46' : isInvestigate ? '#92400e' : '#991b1b' } }, isPursue ? 'PURSUE' : isInvestigate ? 'INVESTIGATE' : 'DEPRIORITIZE'),
                    dr.confidence ? React.createElement('span', { style: { fontSize: 10, color: 'var(--t3)', fontFamily: 'var(--fm)' } }, Math.round(dr.confidence * 100) + '% confidence') : null
                  ),
                  React.createElement('div', { style: { fontSize: 11.5, color: 'var(--t2)', marginTop: 3, lineHeight: 1.5 } }, dr.verdict)
                ),
                /* Estimated cost + timeline */
                React.createElement('div', { style: { textAlign: 'right', minWidth: 100 } },
                  React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 18, fontWeight: 800, color: isPursue ? '#059669' : isInvestigate ? '#d97706' : '#dc2626' } }, '$' + dr.estCostM + 'M'),
                  React.createElement('div', { style: { fontSize: 9, fontWeight: 600, color: 'var(--t3)', letterSpacing: .5, marginTop: 1 } }, 'EST. INVESTMENT'),
                  React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 13, fontWeight: 700, color: 'var(--t2)', marginTop: 4 } }, dr.estYearsLo + '\u2013' + dr.estYearsHi + ' years'),
                  React.createElement('div', { style: { fontSize: 9, fontWeight: 600, color: 'var(--t3)', letterSpacing: .5 } }, 'TO MARKET')
                )
              ),
              /* Dimension scores bar */
              dr.dims ? React.createElement('div', { style: { padding: '0 22px 14px', display: 'flex', gap: 3, flexWrap: 'wrap' } },
                Object.entries(dr.dims).map(function(pair) {
                  var k = pair[0]; var v = pair[1] || 0;
                  var dc = v >= 70 ? '#059669' : v >= 50 ? '#d97706' : '#dc2626';
                  return React.createElement('div', { key: k, style: { flex: '1 1 80px', minWidth: 80 } },
                    React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 } },
                      React.createElement('span', { style: { fontSize: 8.5, fontWeight: 600, color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: .5 } }, k.replace(/_/g, ' ')),
                      React.createElement('span', { style: { fontSize: 10, fontWeight: 800, fontFamily: 'var(--fm)', color: dc } }, v)
                    ),
                    React.createElement('div', { style: { height: 3, borderRadius: 2, background: '#f1f0ee', overflow: 'hidden' } },
                      React.createElement('div', { style: { height: '100%', width: v + '%', borderRadius: 2, background: dc, transition: 'width 1s cubic-bezier(.22,1,.36,1)' } })
                    )
                  );
                })
              ) : null,
              /* Next steps + investment rec */
              (dr.nextSteps && dr.nextSteps.length) || dr.investRec ? React.createElement('div', { style: { padding: '12px 22px 16px', borderTop: '1px solid #f1f0ee', background: '#fafaf9' } },
                dr.investRec ? React.createElement('div', { style: { fontSize: 11, fontWeight: 700, color: isPursue ? '#059669' : isInvestigate ? '#d97706' : '#dc2626', marginBottom: dr.nextSteps && dr.nextSteps.length ? 6 : 0 } }, dr.investRec) : null,
                dr.nextSteps && dr.nextSteps.length ? React.createElement('div', { style: { fontSize: 10.5, color: 'var(--t2)', lineHeight: 1.6 } },
                  dr.nextSteps.map(function(ns, ni) {
                    return React.createElement('span', { key: ni }, (ni > 0 ? ' \u2192 ' : ''), ns);
                  })
                ) : null
              ) : null
            );
          }),
          verdicts.length === 0 ? React.createElement('div', { style: { padding: 20, textAlign: 'center', color: 'var(--t3)' } }, 'No verdict data available.') : null
        ),
        /* Summary stats */
        React.createElement('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 28 } },
          React.createElement('div', { style: { textAlign: 'center', padding: '18px 12px', borderRadius: 14, background: 'linear-gradient(135deg,#f0fdf4,#ecfdf5)', border: '1.5px solid #bbf7d0' } },
            React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 28, fontWeight: 800, color: '#059669' } }, verdicts.filter(function(v) { return v.score >= 70; }).length || '0'),
            React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#059669', letterSpacing: 1 } }, 'PURSUE')
          ),
          React.createElement('div', { style: { textAlign: 'center', padding: '18px 12px', borderRadius: 14, background: 'linear-gradient(135deg,#fffbeb,#fef3c7)', border: '1.5px solid #fde68a' } },
            React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 28, fontWeight: 800, color: '#d97706' } }, verdicts.filter(function(v) { return v.score >= 50 && v.score < 70; }).length || '0'),
            React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#d97706', letterSpacing: 1 } }, 'INVESTIGATE')
          ),
          React.createElement('div', { style: { textAlign: 'center', padding: '18px 12px', borderRadius: 14, background: 'linear-gradient(135deg,#fef2f2,#fff1f2)', border: '1.5px solid #fecaca' } },
            React.createElement('div', { style: { fontFamily: 'var(--fm)', fontSize: 28, fontWeight: 800, color: '#dc2626' } }, verdicts.filter(function(v) { return v.score < 50; }).length || '0'),
            React.createElement('div', { style: { fontSize: 9, fontWeight: 700, color: '#dc2626', letterSpacing: 1 } }, 'DEPRIORITIZE')
          )
        ),
        React.createElement('div', { style: { textAlign: 'center', marginTop: 36 } },
          React.createElement('div', { style: { fontSize: 12, color: 'var(--t3)', marginBottom: 16 } }, '9 agents | 5 databases | 3 adversarial layers' + (((data.meta && data.meta.cost) || 0) > 0 ? ' | $' + data.meta.cost.toFixed(2) : '')),
          React.createElement('button', { className: 'btn-reset', onClick: fullReset }, 'New Investigation')
        )
      ) : null
    )
  );
}

export default function App() {
  return React.createElement(ErrorBoundary, null, React.createElement(AppInner, null));
}
