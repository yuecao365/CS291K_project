const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE";            // 13.33 x 7.5
p.author = "LLM/Agent Course Project";
p.title = "Guidance-Level Policy Verification in Dual-Control Tool Agents";

const W = 13.33, H = 7.5, M = 0.62;

// ---- palette (content-informed: cool=findings, warm=the negative result) ----
const NAVY = "0E1E3A", NAVY2 = "16294C", INK = "1B2A4A", PAPER = "F5F7FB",
      CARD = "FFFFFF", TEAL = "1FA89E", CORAL = "E0563B", STEEL = "5B7AA8",
      MUTE = "7C8696", ICE = "CADCFC", LINE = "DCE3EF";
const HEAD = "Georgia", BODY = "Calibri", MONO = "Consolas";

let pageNo = 0;
const sh = () => ({ type: "outer", color: "000000", blur: 7, offset: 3, angle: 135, opacity: 0.13 });

function bg(s, c) { s.background = { color: c }; }
function footer(s, dark) {
  pageNo++;
  s.addText(`τ²-bench  ·  Guidance-Level Verification`, { x: M, y: H - 0.42, w: 8, h: 0.3,
    fontFace: BODY, fontSize: 10, color: dark ? "6B82AD" : MUTE, align: "left", margin: 0 });
  s.addText(String(pageNo).padStart(2, "0"), { x: W - 1.0, y: H - 0.42, w: 0.4, h: 0.3,
    fontFace: BODY, fontSize: 10, color: dark ? "6B82AD" : MUTE, align: "right", margin: 0 });
}
function kicker(s, txt, x, y, accent) {
  s.addShape(p.shapes.RECTANGLE, { x: x, y: y + 0.02, w: 0.13, h: 0.2, fill: { color: accent } });
  s.addText(txt.toUpperCase(), { x: x + 0.24, y: y - 0.04, w: 10, h: 0.32, fontFace: BODY,
    fontSize: 13.5, bold: true, color: accent, charSpacing: 2, margin: 0, valign: "middle" });
}
function title(s, txt, x, y, w, color, size) {
  s.addText(txt, { x: x, y: y, w: w, h: 1.2, fontFace: HEAD, fontSize: size || 31,
    bold: true, color: color, margin: 0, lineSpacingMultiple: 0.98 });
}

// ============================================================ 1 · TITLE  (unchanged)
(() => {
  const s = p.addSlide(); bg(s, NAVY);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: TEAL } });
  s.addShape(p.shapes.RECTANGLE, { x: 0.22, y: 0, w: 0.08, h: H, fill: { color: CORAL } });
  // (slide 1 edited by author: no kicker / info lines, signed "Yue Cao")
  s.addText("Guidance-Level Policy Verification\nin Dual-Control Tool Agents", { x: 0.95, y: 2.0,
    w: 11.6, h: 2.0, fontFace: HEAD, fontSize: 44, bold: true, color: "FFFFFF", lineSpacingMultiple: 1.02, margin: 0 });
  s.addText("When the user holds the controls — can repairing the agent's guidance recover failures?",
    { x: 1.0, y: 4.15, w: 11.2, h: 0.5, fontFace: BODY, fontSize: 19, color: ICE, italic: true, margin: 0 });
  s.addShape(p.shapes.LINE, { x: 1.0, y: 5.05, w: 3.2, h: 0, line: { color: "33476E", width: 1.5 } });
  s.addText("Yue Cao", { x: 1.0, y: 5.25, w: 11, h: 0.4, fontFace: BODY, fontSize: 15, color: ICE, margin: 0 });
})();

// ============================================================ 2 · SETTING (single vs dual)
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "The setting", M, 0.55, TEAL);
  title(s, "Single-control vs. dual-control", M, 0.92, 12, INK, 30);

  const cw = 5.92, x2 = M + cw + 0.25, cy = 1.95, ch = 3.45;
  const compCard = (x, head, accent, lines) => {
    s.addShape(p.shapes.RECTANGLE, { x, y: cy, w: cw, h: ch, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
    s.addShape(p.shapes.RECTANGLE, { x, y: cy, w: cw, h: 0.62, fill: { color: accent } });
    s.addText(head, { x: x + 0.3, y: cy, w: cw - 0.5, h: 0.62, valign: "middle", fontFace: BODY, fontSize: 15.5, bold: true, color: "FFFFFF", margin: 0 });
    s.addText(lines, { x: x + 0.38, y: cy + 0.85, w: cw - 0.7, h: ch - 1.05, fontFace: BODY, fontSize: 15, color: INK, margin: 0, paraSpaceAfter: 13, lineSpacingMultiple: 1.03 });
  };
  const bl = (arr) => arr.map((t, i) => (typeof t === "string"
    ? { text: t, options: { bullet: true, breakLine: i < arr.length - 1 } }
    : { text: t.t, options: { bullet: true, breakLine: i < arr.length - 1, bold: true, color: t.c } }));
  compCard(M, "SINGLE-CONTROL · τ-bench", NAVY, bl([
    "Only the AGENT acts on the world, via tools.",
    "The user just supplies information.",
    "A verifier can inspect — and BLOCK — the tool call.",
    "Where essentially all prior work lives."]));
  compCard(x2, "DUAL-CONTROL · τ²-bench", CORAL, bl([
    "BOTH agent and user act on a shared world (Dec-POMDP).",
    "The agent must GUIDE the user to take the action.",
    "The user's action cannot be blocked.",
    { t: "The only lever: repair the guidance.", c: CORAL }]));

  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.62, w: 12.09, h: 0.92, fill: { color: "E8F6F4" }, line: { color: TEAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.62, w: 0.13, h: 0.92, fill: { color: TEAL } });
  s.addText([{ text: "The risky action moves from a tool call  →  a natural-language instruction.", options: { bold: true, color: INK } },
    { text: "    Result: an 18–25% pass@1 drop vs. single-control (τ²-bench).", options: { color: TEAL, bold: true } }],
    { x: M + 0.35, y: 5.62, w: 11.6, h: 0.92, valign: "middle", fontFace: BODY, fontSize: 15, margin: 0 });
})();

// ============================================================ 3 · CONCRETE EXAMPLE
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "A concrete example", M, 0.55, CORAL);
  title(s, "“I'm locked out of my account”", M, 0.92, 12, INK, 30);
  s.addText([{ text: "The fix:  ", options: { bold: true, color: CORAL } },
    { text: "the password reset has to be completed by the user — in their own inbox, on their own device.", options: { color: INK } }],
    { x: M, y: 1.78, w: 12, h: 0.35, fontFace: BODY, fontSize: 15, italic: true, margin: 0 });

  const cy = 2.35, ch = 2.95, lw = 4.3, rw = 7.54, rx = M + lw + 0.25;
  // left: single-control handling
  s.addShape(p.shapes.RECTANGLE, { x: M, y: cy, w: lw, h: ch, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
  s.addShape(p.shapes.RECTANGLE, { x: M, y: cy, w: lw, h: 0.58, fill: { color: NAVY } });
  s.addText("IF SINGLE-CONTROL", { x: M + 0.28, y: cy, w: lw - 0.4, h: 0.58, valign: "middle", fontFace: BODY, fontSize: 14.5, bold: true, color: "FFFFFF", margin: 0 });
  s.addText([
    { text: "The agent calls", options: { breakLine: true } },
    { text: "reset_password()", options: { fontFace: MONO, color: NAVY, bold: true, breakLine: true } },
    { text: "with its own tools.", options: { breakLine: true } },
    { text: "\n→ done directly. Nothing to guide.", options: { bold: true, color: TEAL } },
  ], { x: M + 0.3, y: cy + 0.8, w: lw - 0.55, h: ch - 1.0, fontFace: BODY, fontSize: 14.5, color: INK, margin: 0, lineSpacingMultiple: 1.1 });

  // right: dual-control handling
  s.addShape(p.shapes.RECTANGLE, { x: rx, y: cy, w: rw, h: ch, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
  s.addShape(p.shapes.RECTANGLE, { x: rx, y: cy, w: rw, h: 0.58, fill: { color: CORAL } });
  s.addText("DUAL-CONTROL  (reality)", { x: rx + 0.28, y: cy, w: rw - 0.4, h: 0.58, valign: "middle", fontFace: BODY, fontSize: 14.5, bold: true, color: "FFFFFF", margin: 0 });
  s.addText("The reset link lands in the USER's inbox — the agent can't open it. It can only instruct:",
    { x: rx + 0.3, y: cy + 0.72, w: rw - 0.55, h: 0.55, fontFace: BODY, fontSize: 14.5, color: INK, margin: 0, lineSpacingMultiple: 1.05 });
  // guidance bubble
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: rx + 0.3, y: cy + 1.42, w: rw - 0.6, h: 0.66, fill: { color: "FBEAE5" }, line: { color: CORAL, width: 1 }, rectRadius: 0.1 });
  s.addText("“Open the reset email we just sent and click the link to set a new password.”",
    { x: rx + 0.45, y: cy + 1.42, w: rw - 0.9, h: 0.66, valign: "middle", fontFace: BODY, fontSize: 14, italic: true, bold: true, color: "9A3B27", margin: 0 });
  s.addText("The USER performs it. If the agent says this before it has actually sent the email, the user waits — and fails.",
    { x: rx + 0.3, y: cy + 2.2, w: rw - 0.55, h: 0.6, fontFace: BODY, fontSize: 14, color: INK, margin: 0, lineSpacingMultiple: 1.05 });

  s.addText([{ text: "You cannot block a sentence — ", options: { bold: true, color: CORAL } },
    { text: "you can only try to repair it.  That is the entire lever this project studies.", options: { color: INK } }],
    { x: M, y: 5.55, w: 12.09, h: 0.5, fontFace: BODY, fontSize: 15.5, align: "center", margin: 0 });
})();

// ============================================================ 3b · DUAL-CONTROL LOOP (flow)
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "The dual-control loop", M, 0.55, TEAL);
  title(s, "How the default agent actually runs", M, 0.92, 12, INK, 30);

  // legend
  const leg = [["Agent", NAVY], ["User / guidance", CORAL], ["Environment", TEAL]];
  let lx = M;
  leg.forEach(([t, c]) => {
    s.addShape(p.shapes.OVAL, { x: lx, y: 1.99, w: 0.2, h: 0.2, fill: { color: c } });
    s.addText(t, { x: lx + 0.28, y: 1.9, w: 2.4, h: 0.32, valign: "middle", fontFace: BODY, fontSize: 13, color: INK, margin: 0 });
    lx += 0.4 + t.length * 0.105 + 0.55;
  });

  // nodes
  const nodes = [
    { n: "1", tag: "AGENT", t: "Verify identity", sub: "its own tool call", c: NAVY },
    { n: "2", tag: "GUIDANCE", t: "“Click the reset link”", sub: "agent → user (NL)", c: CORAL, msg: true },
    { n: "3", tag: "USER", t: "Clicks link, resets", sub: "on their own device", c: CORAL },
    { n: "4", tag: "ENV", t: "Password updated", sub: "shared state changes", c: TEAL },
    { n: "5", tag: "AGENT", t: "Confirm resolved", sub: "→ success / fail", c: NAVY },
  ];
  const nx0 = M, ny = 2.98, nw = 2.1, nh = 1.62, step = 2.5;
  nodes.forEach((nd, i) => {
    const x = nx0 + i * step;
    const fill = nd.msg ? CARD : nd.c;
    const txtC = nd.msg ? INK : "FFFFFF";
    const subC = nd.msg ? MUTE : ICE;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: ny, w: nw, h: nh, fill: { color: fill }, line: { color: nd.msg ? CORAL : LINE, width: nd.msg ? 1.75 : 1 }, rectRadius: 0.1, shadow: sh() });
    s.addShape(p.shapes.OVAL, { x: x + 0.16, y: ny + 0.16, w: 0.44, h: 0.44, fill: { color: nd.msg ? CORAL : "FFFFFF" }, line: { color: nd.msg ? CORAL : nd.c, width: 1 } });
    s.addText(nd.n, { x: x + 0.16, y: ny + 0.16, w: 0.44, h: 0.44, align: "center", valign: "middle", fontFace: HEAD, fontSize: 15, bold: true, color: nd.msg ? "FFFFFF" : nd.c, margin: 0 });
    s.addText(nd.tag, { x: x + 0.68, y: ny + 0.2, w: nw - 0.78, h: 0.34, valign: "middle", fontFace: BODY, fontSize: 11, bold: true, color: nd.msg ? CORAL : "FFFFFF", charSpacing: 0.8, margin: 0 });
    s.addText(nd.t, { x: x + 0.16, y: ny + 0.72, w: nw - 0.3, h: 0.5, fontFace: BODY, fontSize: 13.5, bold: true, color: txtC, margin: 0, lineSpacingMultiple: 0.95 });
    s.addText(nd.sub, { x: x + 0.16, y: ny + 1.24, w: nw - 0.3, h: 0.32, fontFace: BODY, fontSize: 11, italic: true, color: subC, margin: 0 });
  });
  // arrows between nodes
  for (let i = 0; i < 4; i++) {
    const ax = nx0 + i * step + nw + 0.02;
    s.addShape(p.shapes.LINE, { x: ax, y: ny + nh / 2, w: 0.36, h: 0, line: { color: STEEL, width: 2.5, endArrowType: "triangle" } });
  }
  // emphasize the 2->3 handoff (the risky, un-blockable step)
  const hx = nx0 + 1 * step + nw + 0.02;
  s.addText("user acts", { x: hx - 0.27, y: ny - 0.3, w: 0.9, h: 0.26, align: "center", fontFace: BODY, fontSize: 10.5, bold: true, italic: true, color: CORAL, margin: 0 });

  // callout under the guidance→user handoff (nodes 2–3)
  const cx = nx0 + 1 * step, cwd = nw + 0.4 + nw;
  s.addShape(p.shapes.LINE, { x: cx + cwd / 2, y: ny + nh + 0.06, w: 0, h: 0.3, line: { color: CORAL, width: 2, beginArrowType: "triangle" } });
  s.addShape(p.shapes.RECTANGLE, { x: cx, y: ny + nh + 0.42, w: cwd, h: 0.78, fill: { color: "FBEAE5" }, line: { color: CORAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: cx, y: ny + nh + 0.42, w: 0.12, h: 0.78, fill: { color: CORAL } });
  s.addText([{ text: "The only place I can intervene.  ", options: { bold: true, color: CORAL } },
    { text: "Verify & repair the guidance before the user acts.", options: { color: INK } }],
    { x: cx + 0.3, y: ny + nh + 0.42, w: cwd - 0.5, h: 0.78, valign: "middle", fontFace: BODY, fontSize: 13.5, margin: 0, lineSpacingMultiple: 1.05 });

  // bottom tie
  s.addText([{ text: "Default loop:  ", options: { bold: true, color: INK } },
    { text: "diagnose → guide → user acts → check.  The risky action (steps 2→3) happens on the user's side — you can't block it, only repair the guidance.", options: { color: INK } }],
    { x: M, y: 6.42, w: 12.09, h: 0.5, fontFace: BODY, fontSize: 14, align: "center", margin: 0 });
})();

// ============================================================ 4 · PRIOR WORK GAP
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Where prior work stops", M, 0.55, CORAL);
  title(s, "Everyone verifies the agent's own action — and blocks it", M, 0.92, 12.0, INK, 29);

  const hdr = (t) => ({ text: t, options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, fontSize: 14, align: "left", valign: "middle" } });
  const rows = [
    [hdr("Prior work"), hdr("Verifies"), hdr("Intervention"), hdr("Works in dual-control?")],
    ["Solver-Aided ('26)", "agent's tool call", "block before exec (SMT/Z3)", { text: "✗  user acts, can't block", options: { color: CORAL, bold: true } }],
    ["The Verifier Tax ('26)", "agent action", "block", { text: "“block ≠ success”", options: { color: CORAL } }],
    ["AgentPex / Willful Disobedience", "full trace", "offline diagnosis", { text: "passive (no action)", options: { color: MUTE } }],
    ["DeepVerifier · SETS", "agent's own output", "verify → repair", { text: "single-control only", options: { color: MUTE } }],
  ];
  s.addTable(rows, { x: M, y: 2.0, w: 12.09, colW: [3.0, 2.7, 3.2, 3.19], rowH: [0.5, 0.62, 0.62, 0.62, 0.62],
    fontFace: BODY, fontSize: 14.5, color: INK, valign: "middle", border: { type: "solid", pt: 1, color: LINE },
    fill: { color: CARD }, margin: [3, 6, 3, 6] });

  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.55, w: 12.09, h: 0.95, fill: { color: "FBEAE5" }, line: { color: CORAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.55, w: 0.13, h: 0.95, fill: { color: CORAL } });
  s.addText([{ text: "My angle:  ", options: { bold: true, color: CORAL } },
    { text: "when the user takes the action, blocking is impossible — the only remaining lever is to ", options: {} },
    { text: "repair the natural-language guidance", options: { bold: true } },
    { text: " before the user acts.", options: {} }],
    { x: M + 0.35, y: 5.55, w: 11.6, h: 0.95, valign: "middle", fontFace: BODY, fontSize: 15, color: INK, margin: 0 });
})();

// ============================================================ 5 · HYPOTHESIS (dark)
(() => {
  const s = p.addSlide(); bg(s, NAVY); footer(s, true);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: TEAL } });
  kicker(s, "The idea / hypothesis", 1.0, 1.5, TEAL);
  s.addText("Repair the agent's guidance\nbefore the user acts.", { x: 0.95, y: 2.1, w: 11.6, h: 1.8,
    fontFace: HEAD, fontSize: 40, bold: true, color: "FFFFFF", margin: 0, lineSpacingMultiple: 1.02 });
  s.addText("A verify→repair loop on the agent→user message channel — the one intervention point with no “block” analogue. If failures are guidance-induced, correcting the guidance should recover them.",
    { x: 1.0, y: 4.25, w: 10.8, h: 1.2, fontFace: BODY, fontSize: 18, color: ICE, margin: 0, lineSpacingMultiple: 1.2 });
})();

// ============================================================ 6 · METHOD / PIPELINE (no conditions)
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Method · architecture", M, 0.55, TEAL);
  title(s, "My guidance verify–repair architecture", M, 0.92, 12, INK, 30);

  const ibox = (x, y, w, h, fill, t, sub, tc, sc, bord) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: bord || LINE, width: bord ? 1.75 : 1 }, rectRadius: 0.08, shadow: sh() });
    s.addText([{ text: t, options: { fontSize: 14, bold: true, color: tc, breakLine: true } },
               { text: sub, options: { fontSize: 10.5, color: sc, italic: true } }],
      { x: x + 0.08, y, w: w - 0.16, h, align: "center", valign: "middle", fontFace: BODY, margin: 0, lineSpacingMultiple: 1.05 });
  };

  // ---- AGENT self-loop subsystem ----
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.3, w: 3.95, h: 3.5, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 }, rectRadius: 0.1 });
  s.addText("AGENT  ·  reason ⇄ act loop", { x: M + 0.22, y: 2.42, w: 3.6, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: NAVY, margin: 0 });
  ibox(M + 0.5, 2.95, 2.95, 0.95, NAVY, "AGENT", "LLM policy", "FFFFFF", ICE);
  ibox(M + 0.5, 4.55, 2.95, 0.95, TEAL, "TOOLS / ENV", "look up · status · …", "FFFFFF", "D9F2EF");
  s.addShape(p.shapes.LINE, { x: M + 1.25, y: 3.92, w: 0, h: 0.6, line: { color: STEEL, width: 2.5, endArrowType: "triangle" } });
  s.addText("call tool", { x: M + 0.25, y: 4.08, w: 0.95, h: 0.25, align: "right", fontFace: BODY, fontSize: 10, italic: true, color: MUTE, margin: 0 });
  s.addShape(p.shapes.LINE, { x: M + 2.7, y: 3.92, w: 0, h: 0.6, line: { color: STEEL, width: 2.5, beginArrowType: "triangle" } });
  s.addText("observe", { x: M + 2.8, y: 4.08, w: 0.95, h: 0.25, align: "left", fontFace: BODY, fontSize: 10, italic: true, color: MUTE, margin: 0 });

  // ---- guidance message leaves the agent ----
  s.addShape(p.shapes.LINE, { x: M + 3.95, y: 3.42, w: 0.85, h: 0, line: { color: NAVY, width: 2.5, endArrowType: "triangle" } });
  s.addText("guidance\nmessage", { x: M + 3.78, y: 2.78, w: 1.2, h: 0.55, align: "center", fontFace: BODY, fontSize: 10.5, italic: true, bold: true, color: NAVY, margin: 0, lineSpacingMultiple: 0.9 });

  // ---- MY METHOD: verify → repair ----
  const mx = M + 4.85;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: mx, y: 2.62, w: 4.85, h: 1.95, fill: { color: "FBEAE5" }, line: { color: CORAL, width: 1.75 }, rectRadius: 0.1 });
  s.addText("MY METHOD", { x: mx + 0.22, y: 2.73, w: 4.4, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: CORAL, charSpacing: 1, margin: 0 });
  ibox(mx + 0.3, 3.2, 1.95, 1.05, "FFFFFF", "VERIFY", "check the guidance", CORAL, MUTE, CORAL);
  s.addShape(p.shapes.LINE, { x: mx + 2.33, y: 3.72, w: 0.5, h: 0, line: { color: CORAL, width: 2.5, endArrowType: "triangle" } });
  ibox(mx + 2.9, 3.2, 1.65, 1.05, CORAL, "REPAIR", "rewrite once", "FFFFFF", "FBEAE5");

  // ---- deliver to USER ----
  s.addShape(p.shapes.LINE, { x: mx + 4.85, y: 3.42, w: 0.55, h: 0, line: { color: CORAL, width: 2.5, endArrowType: "triangle" } });
  s.addText("deliver", { x: mx + 4.78, y: 3.0, w: 0.75, h: 0.25, align: "center", fontFace: BODY, fontSize: 10, italic: true, color: MUTE, margin: 0 });
  const ux0 = mx + 5.5;
  ibox(ux0, 2.92, 1.85, 1.05, "FFFFFF", "USER", "acts on the world", CORAL, MUTE, CORAL);

  // ---- outer loop (dashed): user changes the world → agent re-observes ----
  const uc = ux0 + 0.925;
  s.addShape(p.shapes.LINE, { x: uc, y: 3.97, w: 0, h: 2.03, line: { color: STEEL, width: 1.5, dashType: "dash" } });
  s.addShape(p.shapes.LINE, { x: 2.6, y: 6.0, w: uc - 2.6, h: 0, line: { color: STEEL, width: 1.5, dashType: "dash" } });
  s.addShape(p.shapes.LINE, { x: 2.6, y: 5.8, w: 0, h: 0.2, line: { color: STEEL, width: 1.5, dashType: "dash", beginArrowType: "triangle" } });
  s.addText("the user's action changes the shared world  →  the agent observes again and continues",
    { x: M, y: 6.12, w: 12.09, h: 0.35, align: "center", fontFace: BODY, fontSize: 13, italic: true, color: STEEL, margin: 0 });
})();

// ============================================================ 7 · BENCHMARK + TASK + METRICS
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Benchmark & evaluation", M, 0.55, TEAL);
  title(s, "τ²-bench Telecom — what a test task looks like", M, 0.92, 12, INK, 29);

  // left: sample task anatomy (code-ish panel)
  const lw = 7.15, lx = M, ly = 1.95, lh = 3.95;
  s.addShape(p.shapes.RECTANGLE, { x: lx, y: ly, w: lw, h: lh, fill: { color: "0E1E3A" }, line: { color: NAVY, width: 1 }, shadow: sh() });
  s.addText("SAMPLE TASK", { x: lx + 0.3, y: ly + 0.18, w: lw - 0.6, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: TEAL, charSpacing: 1.5, margin: 0 });
  s.addText("[mms_issue]  break_apn · break_app_permission   ·   PERSONA: Hard",
    { x: lx + 0.3, y: ly + 0.5, w: lw - 0.6, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: "FFFFFF", margin: 0 });
  s.addShape(p.shapes.LINE, { x: lx + 0.3, y: ly + 0.92, w: lw - 0.6, h: 0, line: { color: "33476E", width: 1 } });
  const row = (lab, val, yy, valColor) => {
    s.addText(lab, { x: lx + 0.3, y: yy, w: 1.85, h: 0.42, fontFace: MONO, fontSize: 12.5, color: "7C93BD", margin: 0, valign: "top" });
    s.addText(val, { x: lx + 2.2, y: yy, w: lw - 2.5, h: 0.42, fontFace: BODY, fontSize: 14, color: valColor || ICE, margin: 0, valign: "top", lineSpacingMultiple: 1.0 });
  };
  row("initial", "APN misconfigured · MMS app lacks permission", ly + 1.08);
  row("agent tools", "look up line · plan · network status …", ly + 1.55);
  row("user tools", "reset APN · grant permission   (on the device)", ly + 2.02);
  row("success", "env_assertion:  APN == default  AND  permission granted", ly + 2.49, "FFFFFF");
  row("reward", "1.0  if ALL assertions hold at the end, else 0   (binary)", ly + 3.05, TEAL);

  // right: setup + metrics cards
  const rx = lx + lw + 0.3, rw = 12.09 - lw - 0.3;
  const miniCard = (yy, hh, head, accent, lines) => {
    s.addShape(p.shapes.RECTANGLE, { x: rx, y: yy, w: rw, h: hh, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
    s.addShape(p.shapes.RECTANGLE, { x: rx, y: yy, w: 0.13, h: hh, fill: { color: accent } });
    s.addText(head.toUpperCase(), { x: rx + 0.3, y: yy + 0.15, w: rw - 0.5, h: 0.3, fontFace: BODY, fontSize: 13, bold: true, color: accent, charSpacing: 1.2, margin: 0 });
    s.addText(lines, { x: rx + 0.3, y: yy + 0.52, w: rw - 0.55, h: hh - 0.65, fontFace: BODY, fontSize: 14, color: INK, margin: 0, paraSpaceAfter: 6, lineSpacingMultiple: 1.05 });
  };
  const bl = (arr) => arr.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < arr.length - 1 } }));
  miniCard(1.95, 1.9, "Setup", STEEL, bl([
    "Base + user sim: gpt-4.1-mini (temp 0)",
    "Online verifier: gpt-4o-mini",
    "API-only · no training"]));
  miniCard(4.0, 1.9, "Metrics", CORAL, bl([
    "pass@1 · pass^k (reliability)",
    "guidance-induced vs agent-action share",
    "verifier tokens · cost / solved"]));

  s.addText("Two task sets:  telecom_small (20, single-fault, curated)   ·   telecom_full (60 sampled, median 5 faults).",
    { x: M, y: 6.05, w: 12.09, h: 0.4, fontFace: BODY, fontSize: 14, italic: true, color: MUTE, margin: 0 });
})();

// ============================================================ 8 · FIVE CONDITIONS + significance
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Experimental conditions", M, 0.55, CORAL);
  title(s, "Five conditions — an ablation ladder", M, 0.92, 12, INK, 30);

  const hdr = (t) => ({ text: t, options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, fontSize: 14, align: "left", valign: "middle" } });
  const mono = (t, c) => ({ text: t, options: { fontFace: MONO, fontSize: 13.5, bold: true, color: c, valign: "middle" } });
  const rows = [
    [hdr("Condition"), hdr("What it does"), hdr("What it isolates / why")],
    [mono("default", MUTE), "no intervention", "baseline — reproduces the dual-control drop"],
    [mono("action_verifier", MUTE), "verify the agent's own tool calls (no-op on guidance)", { text: "the prior-art paradigm — shows it can't touch guidance failures", options: {} }],
    [mono("self_verify", STEEL), "repair guidance with NO policy grounding", "isolates the value of policy grounding (SETS-style ablation)"],
    [mono("guidance_verify", STEEL), "grounded verify, but NO repair", "isolates detection vs. acting (detect-only)"],
    [mono("guidance_verify_repair", CORAL), "grounded verify + repair", { text: "my full method", options: { bold: true, color: CORAL } }],
  ];
  s.addTable(rows, { x: M, y: 2.0, w: 12.09, colW: [3.35, 4.3, 4.44], rowH: [0.5, 0.6, 0.72, 0.62, 0.6, 0.62],
    fontFace: BODY, fontSize: 14, color: INK, valign: "middle", border: { type: "solid", pt: 1, color: LINE },
    fill: { color: CARD }, margin: [3, 6, 3, 6] });

  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.95, w: 12.09, h: 0.85, fill: { color: "E8F6F4" }, line: { color: TEAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: M, y: 5.95, w: 0.13, h: 0.85, fill: { color: TEAL } });
  s.addText([{ text: "Why this design:  ", options: { bold: true, color: TEAL } },
    { text: "all five share the same base agent and differ ONLY at the hook — so each rung turns off exactly one ingredient, giving clean attribution of where any gain (or harm) comes from.", options: { color: INK } }],
    { x: M + 0.35, y: 5.95, w: 11.6, h: 0.85, valign: "middle", fontFace: BODY, fontSize: 14, margin: 0, lineSpacingMultiple: 1.08 });
})();

// ============================================================ 9 · FINDING 1
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Finding 1 · motivation confirmed", M, 0.55, TEAL);
  title(s, "Most failures are guidance-induced", M, 0.92, 12, INK, 30);
  s.addText("telecom_small · default baseline (20 tasks × 4 trials)", { x: M, y: 1.66, w: 8, h: 0.3, fontFace: BODY, fontSize: 13, italic: true, color: MUTE, margin: 0 });

  // left: the two read-outs (task-level primary, trial-level secondary)
  s.addText("89%", { x: M, y: 2.15, w: 5.7, h: 1.3, fontFace: HEAD, fontSize: 80, bold: true, color: TEAL, margin: 0 });
  s.addText([{ text: "of failing tasks are guidance-induced   ", options: { color: INK } },
    { text: "(8 of 9)", options: { color: MUTE } }],
    { x: M, y: 3.52, w: 5.75, h: 0.5, fontFace: BODY, fontSize: 16, bold: true, margin: 0 });
  s.addText([{ text: "93%", options: { bold: true, color: STEEL } },
    { text: "  counted per trial   (14 of 15)", options: { color: INK } }],
    { x: M, y: 4.18, w: 5.75, h: 0.4, fontFace: BODY, fontSize: 15, margin: 0 });
  s.addText("Attributed via τ²-bench ground-truth: a failed check whose requestor / env_type is \"user\" — the agent had to guide the user, and the guidance failed.",
    { x: M, y: 4.92, w: 5.8, h: 1.1, fontFace: BODY, fontSize: 13.5, italic: true, color: MUTE, margin: 0, lineSpacingMultiple: 1.2 });

  // right: two stacked bars (task vs trial), de-duplication made explicit
  const bx = 7.05, bw = 5.55;
  s.addText("FAILURE COMPOSITION", { x: bx, y: 2.0, w: bw, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: MUTE, charSpacing: 1.5, margin: 0 });
  const bar = (y, label, g, tot) => {
    const frac = g / tot, h = 0.72;
    s.addText(label, { x: bx, y: y - 0.3, w: bw, h: 0.27, fontFace: BODY, fontSize: 12.5, color: INK, margin: 0 });
    s.addShape(p.shapes.RECTANGLE, { x: bx, y, w: bw * frac, h, fill: { color: TEAL } });
    s.addShape(p.shapes.RECTANGLE, { x: bx + bw * frac, y, w: bw * (1 - frac), h, fill: { color: MUTE } });
    s.addText(`guidance  ${g} / ${tot}`, { x: bx, y, w: bw * frac, h, align: "center", valign: "middle", fontFace: BODY, fontSize: 14, bold: true, color: "FFFFFF", margin: 0 });
    s.addText(`${tot - g}`, { x: bx + bw * frac, y, w: bw * (1 - frac), h, align: "center", valign: "middle", fontFace: BODY, fontSize: 12, bold: true, color: "FFFFFF", margin: 0 });
  };
  bar(2.62, "by failing task  ·  n = 9", 8, 9);
  bar(3.95, "by trial  ·  n = 15", 14, 15);
  s.addShape(p.shapes.RECTANGLE, { x: bx, y: 4.95, w: 0.22, h: 0.22, fill: { color: TEAL } });
  s.addText("guidance-induced", { x: bx + 0.3, y: 4.91, w: 2.3, h: 0.3, valign: "middle", fontFace: BODY, fontSize: 12.5, color: INK, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: bx + 2.6, y: 4.95, w: 0.22, h: 0.22, fill: { color: MUTE } });
  s.addText("agent-action", { x: bx + 2.9, y: 4.91, w: 2.3, h: 0.3, valign: "middle", fontFace: BODY, fontSize: 12.5, color: INK, margin: 0 });

  s.addShape(p.shapes.RECTANGLE, { x: bx, y: 5.45, w: bw, h: 1.05, fill: { color: "E8F6F4" }, line: { color: TEAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: bx, y: 5.45, w: 0.13, h: 1.05, fill: { color: TEAL } });
  s.addText([{ text: "The premise holds. ", options: { bold: true, color: TEAL } },
    { text: "Guidance dominates even after de-duplicating repeated failures to distinct tasks — the channel prior blocking-based verifiers cannot touch.", options: { color: INK } }],
    { x: bx + 0.3, y: 5.45, w: bw - 0.5, h: 1.05, valign: "middle", fontFace: BODY, fontSize: 13.5, margin: 0, lineSpacingMultiple: 1.12 });
})();

// ============================================================ 10 · FINDING 2 (bar)
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Finding 2 · the method", M, 0.55, CORAL);
  title(s, "But repair never beats default", M, 0.92, 12, INK, 30);

  const data = [["default", 0.825, NAVY], ["action_verifier", 0.85, STEEL], ["guidance_verify", 0.75, STEEL],
                ["self_verify", 0.75, MUTE], ["guidance_verify_repair", 0.825, CORAL]];
  const baseY = 5.35, maxH = 2.7, scale = maxH / 1.0, x0 = M + 0.3, bw = 1.6, gap = 0.72;
  s.addShape(p.shapes.LINE, { x: x0 - 0.2, y: baseY, w: 11.4, h: 0, line: { color: LINE, width: 1 } });
  s.addShape(p.shapes.LINE, { x: x0 - 0.2, y: baseY - 0.825 * scale, w: 11.4, h: 0, line: { color: NAVY, width: 1, dashType: "dash" } });
  s.addText("← default\n   baseline", { x: 11.9, y: baseY - 0.825 * scale - 0.18, w: 1.3, h: 0.55, fontFace: BODY, fontSize: 10.5, italic: true, color: MUTE, align: "left", margin: 0, lineSpacingMultiple: 0.95 });
  data.forEach(([t, v, c], i) => {
    const x = x0 + i * (bw + gap), h = v * scale;
    s.addShape(p.shapes.RECTANGLE, { x, y: baseY - h, w: bw, h, fill: { color: c } });
    s.addText(v.toFixed(3), { x: x - 0.1, y: baseY - h - 0.32, w: bw + 0.2, h: 0.3, align: "center", fontFace: HEAD, fontSize: 14, bold: true, color: c, margin: 0 });
    s.addText(t, { x: x - 0.35, y: baseY + 0.08, w: bw + 0.7, h: 0.55, align: "center", fontFace: MONO, fontSize: 10.5, color: INK, margin: 0 });
  });
  s.addText("pass@1 — telecom_small, 20 tasks × 2 trials", { x: x0, y: 1.95, w: 8, h: 0.3, fontFace: BODY, fontSize: 13, italic: true, color: MUTE, margin: 0 });

  s.addText([{ text: "Higher-power check (trials=4):  ", options: { bold: true } },
    { text: "default 0.7875  ≥  repair 0.775.   Detect-only & ungrounded self-verify are worse.", options: {} }],
    { x: M, y: 6.45, w: 12, h: 0.4, fontFace: BODY, fontSize: 14.5, color: INK, margin: 0 });
})();

// ============================================================ 11 · FINDING 3 oracle
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Finding 3 · the ceiling (decisive)", M, 0.55, CORAL);
  title(s, "Even a perfect verifier+repair barely moves it", M, 0.92, 12, INK, 30);

  s.addText([{ text: "Oracle upper bound = ", options: { italic: true, color: MUTE } },
    { text: "perfect recall (review every msg) + strong model + perfect selector (per-task max). No real method can exceed it.", options: { italic: true, color: MUTE } }],
    { x: M, y: 1.9, w: 12, h: 0.35, fontFace: BODY, fontSize: 14, margin: 0 });

  const hdr = (t) => ({ text: t, options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, fontSize: 14, align: "center", valign: "middle" } });
  const c = (t, col) => ({ text: t, options: { align: "center", color: col || INK, bold: !!col, fontSize: 15 } });
  const rows = [
    [hdr("Setting"), hdr("default"), hdr("repair-all"), hdr("oracle (max)"), hdr("headroom")],
    [{ text: "telecom_small (20)", options: { fontSize: 14, color: INK } }, c("0.900"), c("0.800", CORAL), c("0.900"), c("+0.000", CORAL)],
    [{ text: "telecom_full (60)", options: { fontSize: 14, color: INK } }, c("0.250"), c("0.200", CORAL), c("0.300"), c("+0.050", CORAL)],
  ];
  s.addTable(rows, { x: M, y: 2.45, w: 12.09, colW: [3.49, 2.15, 2.15, 2.15, 2.15], rowH: [0.55, 0.72, 0.72],
    fontFace: BODY, valign: "middle", border: { type: "solid", pt: 1, color: LINE }, fill: { color: CARD } });

  s.addShape(p.shapes.RECTANGLE, { x: M, y: 4.55, w: 5.92, h: 1.85, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
  s.addShape(p.shapes.RECTANGLE, { x: M, y: 4.55, w: 0.13, h: 1.85, fill: { color: STEEL } });
  s.addText([{ text: "Easy set = ceiling effect\n", options: { bold: true, color: STEEL, fontSize: 15 } },
    { text: "default already 0.900; the 2 residual failures are timeouts, not guidance violations.", options: { color: INK, fontSize: 13.5 } }],
    { x: M + 0.35, y: 4.55, w: 5.4, h: 1.85, valign: "middle", fontFace: BODY, margin: 0, lineSpacingMultiple: 1.1 });

  s.addShape(p.shapes.RECTANGLE, { x: M + 6.17, y: 4.55, w: 5.92, h: 1.85, fill: { color: "FBEAE5" }, line: { color: CORAL, width: 1 } });
  s.addShape(p.shapes.RECTANGLE, { x: M + 6.17, y: 4.55, w: 0.13, h: 1.85, fill: { color: CORAL } });
  s.addText([{ text: "Hard set = real but tiny\n", options: { bold: true, color: CORAL, fontSize: 15 } },
    { text: "repair fixed 3 real failures but BROKE 6. Net-negative; ceiling only +0.050 (3/60).", options: { color: INK, fontSize: 13.5 } }],
    { x: M + 6.52, y: 4.55, w: 5.4, h: 1.85, valign: "middle", fontFace: BODY, margin: 0, lineSpacingMultiple: 1.1 });
})();

// ============================================================ 13 · ANALYSIS
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Analysis", M, 0.55, CORAL);
  title(s, "Limitations of my experiments", M, 0.92, 12, INK, 30);

  const lims = [
    ["Small, narrow sample", "Only ~9 of 20 tasks ever fail — a few-task gap sits within noise. trials = 2–4, no confidence intervals."],
    ["Noise ≥ the effect", "guidance_verify is a no-op control, yet differs ±0.05 from default at temp 0.7 — the same size as the oracle headroom."],
    ["Limited coverage", "The full 5-method comparison is only on the easy (ceiling) set; the hard set has just the oracle bound. One base agent, one domain."],
    ["Simulated users", "The user is an LLM simulator — its behaviour may not match how real users follow guidance."],
  ];
  const cw = 5.9, ch = 1.95, gx = M, gy = 2.1, gp = 0.27;
  lims.forEach((it, i) => {
    const x = gx + (i % 2) * (cw + gp), y = gy + Math.floor(i / 2) * (ch + gp);
    s.addShape(p.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: CARD }, line: { color: LINE, width: 1 }, shadow: sh() });
    s.addShape(p.shapes.RECTANGLE, { x, y, w: 0.13, h: ch, fill: { color: CORAL } });
    s.addText(it[0], { x: x + 0.4, y: y + 0.28, w: cw - 0.7, h: 0.45, fontFace: BODY, fontSize: 17, bold: true, color: INK, margin: 0 });
    s.addText(it[1], { x: x + 0.4, y: y + 0.82, w: cw - 0.75, h: 1.0, fontFace: BODY, fontSize: 13.5, color: INK, margin: 0, lineSpacingMultiple: 1.12 });
  });
})();

// ============================================================ 14 · FUTURE WORK
(() => {
  const s = p.addSlide(); bg(s, PAPER); footer(s, false);
  kicker(s, "Future work", M, 0.55, TEAL);
  title(s, "What I'd try next", M, 0.92, 12, INK, 30);

  const rows = [
    ["1", "Run more experiments across difficulty levels", "Run the real methods — not just the oracle — on the harder, multi-fault tasks; add more trials, and try other domains.", TEAL],
    ["2", "Adjust the architecture", "Move the check to the agent's plan / diagnosis instead of the final guidance message.", NAVY],
    ["3", "Make repair more conservative", "Fire repair only when the verifier is confident, so it stops breaking correct guidance.", STEEL],
    ["4", "Finer error analysis", "Trace which step in the conversation caused each failure — not just the final outcome.", CORAL],
  ];
  let y = 2.0; const rh = 1.2;
  rows.forEach((r) => {
    s.addShape(p.shapes.OVAL, { x: M, y: y, w: 0.72, h: 0.72, fill: { color: r[3] } });
    s.addText(r[0], { x: M, y: y, w: 0.72, h: 0.72, align: "center", valign: "middle", fontFace: HEAD, fontSize: 26, bold: true, color: "FFFFFF", margin: 0 });
    s.addText(r[1], { x: M + 1.05, y: y - 0.02, w: 11, h: 0.5, fontFace: BODY, fontSize: 20, bold: true, color: INK, margin: 0 });
    s.addText(r[2], { x: M + 1.05, y: y + 0.55, w: 10.8, h: 0.7, fontFace: BODY, fontSize: 15, color: MUTE, margin: 0, lineSpacingMultiple: 1.12 });
    y += rh;
  });
})();

// ============================================================ 15 · THANK YOU (dark)
(() => {
  const s = p.addSlide(); bg(s, NAVY);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: TEAL } });
  s.addShape(p.shapes.RECTANGLE, { x: 0.22, y: 0, w: 0.08, h: H, fill: { color: CORAL } });
  s.addText("Thank you.", { x: 1.0, y: 2.3, w: 11, h: 1.3, fontFace: HEAD, fontSize: 60, bold: true, color: "FFFFFF", margin: 0 });
  s.addText("Dual-control failures are guidance-induced — but repairing the guidance can't recover them. The real lever is the agent's diagnosis.",
    { x: 1.02, y: 3.85, w: 10.8, h: 1.0, fontFace: BODY, fontSize: 18, italic: true, color: ICE, margin: 0, lineSpacingMultiple: 1.25 });
  s.addShape(p.shapes.LINE, { x: 1.05, y: 5.2, w: 3.2, h: 0, line: { color: "33476E", width: 1.5 } });
  s.addText([{ text: "Yue Cao", options: { bold: true, color: "FFFFFF" } },
    { text: "        Questions welcome", options: { color: "7C93BD" } }],
    { x: 1.05, y: 5.4, w: 11, h: 0.4, fontFace: BODY, fontSize: 16, margin: 0 });
})();

p.writeFile({ fileName: process.env.OUTFILE || "Guidance_Verification_DualControl.pptx" }).then(f => console.log("WROTE " + f));
