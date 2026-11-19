/**
 * FitTrack 3D Night Marathon & Stadium Track Engine (Three.js WebGL)
 * Powers both the full-viewport interactive 7-stage Landing Course and the
 * personalized live Dashboard 3D Track Arena.
 */
import * as THREE from "/static/vendor/three-bundle.js";
import { RoomEnvironment } from "/static/vendor/three-bundle.js";

// Detect software WebGL via GPU renderer string only (never UA)
function detectSoftwareGl() {
  try {
    const probeCanvas = document.createElement("canvas");
    const gl =
      probeCanvas.getContext("webgl2") || probeCanvas.getContext("webgl");
    if (!gl) return true;
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
    const gpu = String(gl.getParameter(param) || "");
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
  } catch (_) {
    return true;
  }
}

// Procedural texture generators (100% zero external files, crisp SRGBColorSpace)
function createTrackTexture(maxAnisotropy) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");

  // Terracotta rubberized track base
  ctx.fillStyle = "#b5422c";
  ctx.fillRect(0, 0, 512, 512);

  // Subtle rubber grain speckles
  for (let i = 0; i < 4200; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 512;
    ctx.fillStyle =
      Math.random() > 0.5 ? "rgba(255,215,190,0.08)" : "rgba(42,12,6,0.12)";
    ctx.fillRect(x, y, 2, 2);
  }

  // Dark shoulder curbs on left & right edges
  ctx.fillStyle = "#262c29";
  ctx.fillRect(0, 0, 26, 512);
  ctx.fillRect(486, 0, 26, 512);

  // Acid-lime outer border accent strips
  ctx.fillStyle = "#d4ff2b";
  ctx.fillRect(22, 0, 4, 512);
  ctx.fillRect(486, 0, 4, 512);

  // 6 crisp running lanes with white dividing lines
  const innerStart = 32;
  const innerWidth = 448;
  const laneCount = 6;
  const laneW = innerWidth / laneCount;

  // Alternate subtle lane shading
  for (let l = 0; l < laneCount; l++) {
    if (l % 2 === 1) {
      ctx.fillStyle = "rgba(0,0,0,0.06)";
      ctx.fillRect(innerStart + l * laneW, 0, laneW, 512);
    }
  }

  ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
  for (let l = 0; l <= laneCount; l++) {
    const x = Math.round(innerStart + l * laneW) - 2;
    ctx.fillRect(x, 0, l === 0 || l === laneCount ? 5 : 3.5, 512);
  }

  // Center lane subtle chevron speed guide
  ctx.fillStyle = "rgba(212, 255, 43, 0.24)";
  const centerX = innerStart + 2.5 * laneW;
  for (let y = 32; y < 512; y += 128) {
    ctx.beginPath();
    ctx.moveTo(centerX, y);
    ctx.lineTo(centerX + 18, y + 26);
    ctx.lineTo(centerX + 9, y + 26);
    ctx.lineTo(centerX, y + 12);
    ctx.lineTo(centerX - 9, y + 26);
    ctx.lineTo(centerX - 18, y + 26);
    ctx.closePath();
    ctx.fill();
  }

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 34);
  tex.anisotropy = maxAnisotropy;
  return tex;
}

function createSignCanvasTexture(
  title,
  subtitle,
  bgColor,
  fgColor,
  accentColor,
  maxAnisotropy
) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 256;
  const ctx = c.getContext("2d");

  ctx.fillStyle = bgColor;
  ctx.fillRect(0, 0, 512, 256);

  // Subtle top accent bar
  ctx.fillStyle = accentColor;
  ctx.fillRect(0, 0, 512, 16);

  // Crisp inner border
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 4;
  ctx.strokeRect(14, 28, 484, 214);

  // Main display headline
  ctx.fillStyle = fgColor;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "900 68px 'Barlow Condensed', Impact, sans-serif";
  ctx.fillText(title, 256, subtitle ? 116 : 138);

  if (subtitle) {
    ctx.fillStyle = accentColor;
    ctx.font = "700 26px 'JetBrains Mono', monospace";
    ctx.fillText(subtitle, 256, 188);
  }

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAnisotropy;
  return tex;
}

function createDistanceMarkerTexture(label, maxAnisotropy) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 140;
  const ctx = c.getContext("2d");

  ctx.fillStyle = "#f5f5ee";
  ctx.fillRect(0, 0, 256, 140);

  ctx.fillStyle = "#d4ff2b";
  ctx.fillRect(0, 0, 256, 22);

  ctx.strokeStyle = "#161a18";
  ctx.lineWidth = 6;
  ctx.strokeRect(3, 3, 250, 134);

  ctx.fillStyle = "#111513";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "900 72px 'JetBrains Mono', monospace";
  ctx.fillText(label, 128, 84);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAnisotropy;
  return tex;
}

function createBuildingWindowTexture(maxAnisotropy) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 512;
  const ctx = c.getContext("2d");

  ctx.fillStyle = "#101614";
  ctx.fillRect(0, 0, 256, 512);

  const cols = 6;
  const rows = 18;
  const padX = 14;
  const padY = 12;
  const w = (256 - padX * (cols + 1)) / cols;
  const h = (512 - padY * (rows + 1)) / rows;

  for (let r = 0; r < rows; r++) {
    for (let col = 0; col < cols; col++) {
      const lit = Math.random();
      if (lit > 0.62) {
        ctx.fillStyle =
          lit > 0.92
            ? "rgba(212, 255, 43, 0.72)"
            : lit > 0.76
            ? "rgba(255, 214, 122, 0.85)"
            : "rgba(255, 240, 200, 0.45)";
      } else {
        ctx.fillStyle = "rgba(35, 48, 43, 0.45)";
      }
      ctx.fillRect(
        padX + col * (w + padX),
        padY + r * (h + padY),
        w,
        h
      );
    }
  }

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = maxAnisotropy;
  return tex;
}

// Build a ribbon BufferGeometry along a CatmullRomCurve3
function buildCurvedRibbon(curve, width, segments, yOffset = 0.03) {
  const positions = [];
  const normals = [];
  const uvs = [];
  const indices = [];

  const up = new THREE.Vector3(0, 1, 0);
  const right = new THREE.Vector3();

  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const pt = curve.getPointAt(t);
    const tangent = curve.getTangentAt(t).normalize();
    right.crossVectors(tangent, up).normalize();

    const leftX = pt.x - right.x * (width * 0.5);
    const leftZ = pt.z - right.z * (width * 0.5);
    const rightX = pt.x + right.x * (width * 0.5);
    const rightZ = pt.z + right.z * (width * 0.5);

    positions.push(leftX, pt.y + yOffset, leftZ);
    positions.push(rightX, pt.y + yOffset, rightZ);
    normals.push(0, 1, 0, 0, 1, 0);
    uvs.push(0, t, 1, t);

    if (i < segments) {
      const base = i * 2;
      indices.push(base, base + 1, base + 2);
      indices.push(base + 1, base + 3, base + 2);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  return geo;
}

// Composite 3D Gantry Arch (10+ parts: footings, truss pillars, overhead box, sign board, 3 race lights, side chevrons)
function createGantryArch(label, subtitle, maxAnisotropy, isStart = false) {
  const group = new THREE.Group();

  const frameMat = new THREE.MeshStandardMaterial({
    color: 0x161c19,
    metalness: 0.65,
    roughness: 0.32,
  });
  const footingMat = new THREE.MeshStandardMaterial({
    color: 0x2c3430,
    metalness: 0.15,
    roughness: 0.82,
  });
  const trimMat = new THREE.MeshStandardMaterial({
    color: 0xd4ff2b,
    emissive: 0xbef200,
    emissiveIntensity: 0.9,
    roughness: 0.25,
    metalness: 0.2,
  });

  const halfSpan = 5.6;
  const height = 6.2;

  [-halfSpan, halfSpan].forEach((x) => {
    const footing = new THREE.Mesh(
      new THREE.BoxGeometry(0.95, 0.7, 0.95),
      footingMat
    );
    footing.position.set(x, 0.35, 0);
    group.add(footing);

    const pillar = new THREE.Mesh(
      new THREE.BoxGeometry(0.45, height, 0.45),
      frameMat
    );
    pillar.position.set(x, height * 0.5, 0);
    pillar.castShadow = true;
    group.add(pillar);

    // Side glowing chevron bars
    for (let c = 0; c < 2; c++) {
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(0.12, 0.42, 0.52),
        trimMat
      );
      bar.position.set(x, 4.1 + c * 0.7, 0);
      group.add(bar);
    }
  });

  // Main overhead beam cabinet
  const beam = new THREE.Mesh(
    new THREE.BoxGeometry(halfSpan * 2 + 0.6, 1.9, 0.75),
    frameMat
  );
  beam.position.set(0, height - 0.3, 0);
  beam.castShadow = true;
  group.add(beam);

  // Illuminated top trim strip
  const topTrim = new THREE.Mesh(
    new THREE.BoxGeometry(halfSpan * 2 + 0.68, 0.12, 0.8),
    trimMat
  );
  topTrim.position.set(0, height + 0.68, 0);
  group.add(topTrim);

  // Front & back sign panels
  const signTex = createSignCanvasTexture(
    label,
    subtitle,
    "#0f1412",
    "#d4ff2b",
    "#f5f5ee",
    maxAnisotropy
  );
  const signMat = new THREE.MeshStandardMaterial({
    map: signTex,
    emissive: new THREE.Color(0x9be214),
    emissiveMap: signTex,
    emissiveIntensity: 0.65,
    roughness: 0.35,
    metalness: 0.1,
  });

  const signFront = new THREE.Mesh(new THREE.PlaneGeometry(8.8, 1.65), signMat);
  signFront.position.set(0, height - 0.3, 0.4);
  group.add(signFront);

  const signBack = new THREE.Mesh(new THREE.PlaneGeometry(8.8, 1.65), signMat);
  signBack.position.set(0, height - 0.3, -0.4);
  signBack.rotation.y = Math.PI;
  group.add(signBack);

  // 3 race countdown lights under START gantry (matching reference screenshot!)
  const lights = [];
  if (isStart) {
    [-1.4, 0, 1.4].forEach((lx) => {
      const bezel = new THREE.Mesh(
        new THREE.CylinderGeometry(0.36, 0.36, 0.18, 16),
        footingMat
      );
      bezel.rotation.x = Math.PI / 2;
      bezel.position.set(lx, height - 1.55, 0.22);
      group.add(bezel);

      const bulbMat = new THREE.MeshStandardMaterial({
        color: 0xd4ff2b,
        emissive: 0xd4ff2b,
        emissiveIntensity: 1.45,
        roughness: 0.2,
      });
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.28, 16, 12), bulbMat);
      bulb.position.set(lx, height - 1.55, 0.32);
      group.add(bulb);
      lights.push(bulbMat);
    });
  }

  group.userData.raceLights = lights;
  return group;
}

// Composite 3D Animated Runner / FitBuddy Pacemaker (10 parts, grounded bottom-center pivot)
function createRunnerFigure() {
  const runner = new THREE.Group();

  const suitMat = new THREE.MeshStandardMaterial({
    color: 0x161e1a,
    roughness: 0.55,
    metalness: 0.12,
  });
  const limeMat = new THREE.MeshStandardMaterial({
    color: 0xd4ff2b,
    emissive: 0x99cc00,
    emissiveIntensity: 0.65,
    roughness: 0.25,
    metalness: 0.2,
  });
  const skinMat = new THREE.MeshStandardMaterial({
    color: 0xf6c39c,
    roughness: 0.65,
    metalness: 0.02,
  });
  const shoeMat = new THREE.MeshStandardMaterial({
    color: 0xf5f5ee,
    roughness: 0.4,
    metalness: 0.1,
  });
  const accentCoralMat = new THREE.MeshStandardMaterial({
    color: 0xee5a3a,
    roughness: 0.35,
    metalness: 0.15,
  });

  // Body pivot for bounce/lean
  const body = new THREE.Group();
  runner.add(body);

  // Torso jacket + glowing race bib plate
  const torso = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.32, 0.58, 6, 12),
    suitMat
  );
  torso.position.y = 1.28;
  torso.castShadow = true;
  body.add(torso);

  const bib = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.34, 0.08), shoeMat);
  bib.position.set(0, 1.32, -0.31);
  body.add(bib);

  const bibStripe = new THREE.Mesh(
    new THREE.BoxGeometry(0.42, 0.08, 0.09),
    limeMat
  );
  bibStripe.position.set(0, 1.46, -0.31);
  body.add(bibStripe);

  // Head + athletic headband/visor
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.28, 16, 14), skinMat);
  head.position.y = 1.98;
  head.castShadow = true;
  body.add(head);

  const headband = new THREE.Mesh(
    new THREE.CylinderGeometry(0.295, 0.295, 0.11, 16),
    limeMat
  );
  headband.position.y = 2.08;
  body.add(headband);

  // Left & Right Arms (pivoted at shoulders)
  const leftArmPivot = new THREE.Group();
  leftArmPivot.position.set(-0.42, 1.52, 0);
  const armGeo = new THREE.CapsuleGeometry(0.11, 0.42, 4, 8);
  const leftArm = new THREE.Mesh(armGeo, accentCoralMat);
  leftArm.position.y = -0.22;
  leftArmPivot.add(leftArm);
  body.add(leftArmPivot);

  const rightArmPivot = new THREE.Group();
  rightArmPivot.position.set(0.42, 1.52, 0);
  const rightArm = new THREE.Mesh(armGeo, accentCoralMat);
  rightArm.position.y = -0.22;
  rightArmPivot.add(rightArm);
  body.add(rightArmPivot);

  // Left & Right Legs + Sneakers (pivoted at hips)
  const legGeo = new THREE.CapsuleGeometry(0.13, 0.52, 4, 8);
  const shoeGeo = new THREE.BoxGeometry(0.22, 0.14, 0.42);

  const leftLegPivot = new THREE.Group();
  leftLegPivot.position.set(-0.18, 0.82, 0);
  const leftLeg = new THREE.Mesh(legGeo, suitMat);
  leftLeg.position.y = -0.32;
  const leftShoe = new THREE.Mesh(shoeGeo, limeMat);
  leftShoe.position.set(0, -0.72, 0.08);
  leftLegPivot.add(leftLeg, leftShoe);
  body.add(leftLegPivot);

  const rightLegPivot = new THREE.Group();
  rightLegPivot.position.set(0.18, 0.82, 0);
  const rightLeg = new THREE.Mesh(legGeo, suitMat);
  rightLeg.position.y = -0.32;
  const rightShoe = new THREE.Mesh(shoeGeo, limeMat);
  rightShoe.position.set(0, -0.72, 0.08);
  rightLegPivot.add(rightLeg, rightShoe);
  body.add(rightLegPivot);

  // Ground contact glow ring beneath runner
  const glowRing = new THREE.Mesh(
    new THREE.RingGeometry(0.32, 0.65, 24),
    new THREE.MeshBasicMaterial({
      color: 0xd4ff2b,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
  );
  glowRing.rotation.x = -Math.PI / 2;
  glowRing.position.y = 0.06;
  runner.add(glowRing);

  runner.userData = {
    body,
    leftArmPivot,
    rightArmPivot,
    leftLegPivot,
    rightLegPivot,
    glowRing,
  };
  return runner;
}

// Composite Trackside Streetlamp (6 parts)
function createLampPost(sideSign) {
  const g = new THREE.Group();
  const poleMat = new THREE.MeshStandardMaterial({
    color: 0x202724,
    metalness: 0.72,
    roughness: 0.34,
  });
  const glowMat = new THREE.MeshStandardMaterial({
    color: 0xfff3c4,
    emissive: 0xffd166,
    emissiveIntensity: 2.2,
    roughness: 0.15,
  });

  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.3, 0.5, 8), poleMat);
  base.position.y = 0.25;
  g.add(base);

  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 5.4, 8), poleMat);
  pole.position.y = 2.95;
  g.add(pole);

  const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.1, 0.1), poleMat);
  arm.position.set(-sideSign * 0.72, 5.55, 0);
  g.add(arm);

  const housing = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.16, 0.3), poleMat);
  housing.position.set(-sideSign * 1.35, 5.46, 0);
  g.add(housing);

  const bulb = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.08, 0.22), glowMat);
  bulb.position.set(-sideSign * 1.35, 5.36, 0);
  g.add(bulb);

  // Soft warm light pool on the track edge
  const pool = new THREE.Mesh(
    new THREE.CircleGeometry(2.1, 18),
    new THREE.MeshBasicMaterial({
      color: 0xffd166,
      transparent: true,
      opacity: 0.12,
      depthWrite: false,
    })
  );
  pool.rotation.x = -Math.PI / 2;
  pool.position.set(-sideSign * 1.35, 0.055, 0);
  g.add(pool);

  return g;
}

// Composite Billboard alongside the course
function createTrackBillboard(title, subtitle, maxAnisotropy) {
  const g = new THREE.Group();
  const postMat = new THREE.MeshStandardMaterial({
    color: 0x202724,
    metalness: 0.6,
    roughness: 0.4,
  });

  [-1.6, 1.6].forEach((px) => {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.18, 2.2, 0.18), postMat);
    leg.position.set(px, 1.1, 0);
    g.add(leg);
  });

  const backing = new THREE.Mesh(new THREE.BoxGeometry(4.4, 2.2, 0.24), postMat);
  backing.position.set(0, 2.6, 0);
  g.add(backing);

  const tex = createSignCanvasTexture(
    title,
    subtitle,
    "#121815",
    "#f5f5ee",
    "#d4ff2b",
    maxAnisotropy
  );
  const faceMat = new THREE.MeshStandardMaterial({
    map: tex,
    emissive: new THREE.Color(0xffffff),
    emissiveMap: tex,
    emissiveIntensity: 0.35,
    roughness: 0.4,
  });
  const face = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 2.0), faceMat);
  face.position.set(0, 2.6, 0.14);
  g.add(face);

  return g;
}

/**
 * Main interactive 3D Night Track controller
 */
export function initFitTrack3D(container, options = {}) {
  if (!container) return null;

  const mode = options.mode || "landing"; // 'landing' | 'dashboard'
  const stages = options.stages || [];
  const initialProgress = Number(options.initialProgress || 0);
  const prefersReducedMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const isSoftwareGl = detectSoftwareGl();

  // Mount canvas inside dedicated empty mount div
  const mountEl = container.querySelector("[data-webgl-mount]") || container;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: !isSoftwareGl,
      powerPreference: "high-performance",
      alpha: false,
    });
  } catch (err) {
    container.classList.add("webgl-fallback-active");
    return null;
  }

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.14;
  renderer.setPixelRatio(
    isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2)
  );
  renderer.shadowMap.enabled = !isSoftwareGl;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setSize(mountEl.clientWidth || 960, mountEl.clientHeight || 560);
  renderer.domElement.style.display = "block";
  renderer.domElement.style.width = "100%";
  renderer.domElement.style.height = "100%";

  mountEl.innerHTML = "";
  mountEl.appendChild(renderer.domElement);

  const maxAnisotropy = renderer.capabilities.getMaxAnisotropy();

  // Scene + Atmospheric Night Fog
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0f0d);
  scene.fog = new THREE.FogExp2(0x0a0f0d, mode === "dashboard" ? 0.015 : 0.0115);

  // Mandatory Studio Environment Reflection (RoomEnvironment)
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.45;
  pmrem.dispose();

  // Camera
  const baseFov = mode === "dashboard" ? 56 : 54;
  const camera = new THREE.PerspectiveCamera(
    baseFov,
    (mountEl.clientWidth || 960) / Math.max(1, mountEl.clientHeight || 560),
    0.1,
    340
  );

  // Warm/Cool 3-Point Stadium Night Lighting Rig (<= 2 shadow casters)
  const hemiLight = new THREE.HemisphereLight(0x88b4ff, 0x1a261e, 0.72);
  scene.add(hemiLight);

  const keyLight = new THREE.DirectionalLight(0xffe7b8, 1.55);
  keyLight.position.set(22, 42, 26);
  if (!isSoftwareGl) {
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(1024, 1024);
    keyLight.shadow.camera.near = 2;
    keyLight.shadow.camera.far = 140;
    keyLight.shadow.camera.left = -40;
    keyLight.shadow.camera.right = 40;
    keyLight.shadow.camera.top = 40;
    keyLight.shadow.camera.bottom = -40;
    keyLight.shadow.bias = -0.0005;
    keyLight.shadow.normalBias = 0.02;
  }
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0xc8ff2b, 0.65);
  rimLight.position.set(-28, 18, -60);
  scene.add(rimLight);

  // Runner Point Glow (follows the runner down the track)
  const runnerGlowLight = new THREE.PointLight(0xd4ff2b, 2.2, 16, 1.6);
  scene.add(runnerGlowLight);

  // Winding S-Curve Marathon Course Path (length ~ 280 units)
  const controlPoints = [
    new THREE.Vector3(0, 0, 12),
    new THREE.Vector3(0, 0, -18),
    new THREE.Vector3(6, 0.3, -54),
    new THREE.Vector3(-4, 0.5, -96),
    new THREE.Vector3(-12, 0.2, -142),
    new THREE.Vector3(4, 0.4, -186),
    new THREE.Vector3(14, 0.2, -230),
    new THREE.Vector3(2, 0, -274),
    new THREE.Vector3(0, 0, -312),
  ];
  const trackCurve = new THREE.CatmullRomCurve3(controlPoints, false, "catmullrom", 0.5);

  // Extended Rolling Outdoor Ground Terrain (never boxed in!)
  const groundGeo = new THREE.PlaneGeometry(420, 480, 48, 56);
  groundGeo.rotateX(-Math.PI / 2);
  const posAttr = groundGeo.attributes.position;
  for (let i = 0; i < posAttr.count; i++) {
    const gx = posAttr.getX(i);
    const gz = posAttr.getZ(i);
    const approxCenter = Math.sin(gz * 0.025) * 9;
    const distFromTrack = Math.abs(gx - approxCenter);
    const hill =
      distFromTrack > 14
        ? Math.sin(gx * 0.06) * Math.cos(gz * 0.05) * Math.min(3.5, (distFromTrack - 14) * 0.14)
        : 0;
    posAttr.setY(i, hill - 0.08);
  }
  groundGeo.computeVertexNormals();
  const groundMat = new THREE.MeshStandardMaterial({
    color: 0x1a221d,
    roughness: 0.92,
    metalness: 0.04,
    flatShading: true,
  });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.position.set(0, 0, -145);
  ground.receiveShadow = true;
  scene.add(ground);

  // 6-Lane Curved Terracotta Running Track Ribbon
  const trackTex = createTrackTexture(maxAnisotropy);
  const trackGeo = buildCurvedRibbon(trackCurve, 8.8, 220, 0.03);
  const trackMat = new THREE.MeshStandardMaterial({
    map: trackTex,
    roughness: 0.68,
    metalness: 0.08,
  });
  const trackMesh = new THREE.Mesh(trackGeo, trackMat);
  trackMesh.receiveShadow = true;
  scene.add(trackMesh);

  // Glowing Neon-Lime Center Pace Trail Ribbon (offset +0.06 on Y so zero Z-fighting)
  const trailGeo = buildCurvedRibbon(trackCurve, 0.24, 220, 0.06);
  const trailMat = new THREE.MeshBasicMaterial({
    color: 0xd4ff2b,
    transparent: true,
    opacity: 0.78,
  });
  const trailMesh = new THREE.Mesh(trailGeo, trailMat);
  scene.add(trailMesh);

  // Starry Night Sky Dome (Instanced Points)
  const starCount = 650;
  const starPositions = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    starPositions[i * 3] = (Math.random() - 0.5) * 320;
    starPositions[i * 3 + 1] = 16 + Math.random() * 95;
    starPositions[i * 3 + 2] = 40 - Math.random() * 400;
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  const starMat = new THREE.PointsMaterial({
    color: 0xf4f8eb,
    size: 0.68,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.85,
  });
  const starField = new THREE.Points(starGeo, starMat);
  scene.add(starField);

  // Helper to place objects oriented cleanly along the curve
  const _up = new THREE.Vector3(0, 1, 0);
  const _right = new THREE.Vector3();
  const _pt = new THREE.Vector3();
  const _tan = new THREE.Vector3();

  function orientAlongCurve(obj, t, lateralOffset = 0, faceForward = true) {
    trackCurve.getPointAt(t, _pt);
    trackCurve.getTangentAt(t, _tan).normalize();
    _right.crossVectors(_tan, _up).normalize();

    obj.position.set(
      _pt.x + _right.x * lateralOffset,
      _pt.y,
      _pt.z + _right.z * lateralOffset
    );
    const angle = Math.atan2(_tan.x, _tan.z);
    obj.rotation.y = faceForward ? angle + Math.PI : angle;
  }

  // START Gantry at t = 0.065 & FINISH Gantry at t = 0.94
  const startGantry = createGantryArch(
    "START",
    "FITTRACK NIGHT RUN",
    maxAnisotropy,
    true
  );
  orientAlongCurve(startGantry, 0.068, 0, true);
  scene.add(startGantry);

  const finishGantry = createGantryArch(
    "FINISH",
    "EVERY GOAL UNLOCKS SOMETHING",
    maxAnisotropy,
    true
  );
  orientAlongCurve(finishGantry, 0.94, 0, true);
  scene.add(finishGantry);

  // Distance Markers (01K .. 07K) & Trackside Feature Billboards
  const billboardCopy = [
    { t: 0.16, side: 1, km: "01K", title: "10+ EXERCISES", sub: "GUIDED LIVE TIMERS" },
    { t: 0.29, side: -1, km: "02K", title: "7+ SPORTS IDEAS", sub: "SPIN WHAT TO PLAY" },
    { t: 0.43, side: 1, km: "03K", title: "REWARD JARS", sub: "WATCH GOALS FILL LIVE" },
    { t: 0.57, side: -1, km: "04K", title: "FITBUDDY COACH", sub: "NOVA & ATLAS CHEER YOU" },
    { t: 0.71, side: 1, km: "05K", title: "DAILY STREAKS", sub: "KEEP THE FLAME ALIVE" },
    { t: 0.84, side: -1, km: "06K", title: "8 TROPHY BADGES", sub: "EARN REAL WORKOUT XP" },
  ];

  const markerPoleMat = new THREE.MeshStandardMaterial({
    color: 0xe5e7eb,
    metalness: 0.5,
    roughness: 0.35,
  });

  billboardCopy.forEach((b) => {
    // Crisp white/lime KM sign board near the curb
    const kmGroup = new THREE.Group();
    const stake = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 1.35, 8),
      markerPoleMat
    );
    stake.position.y = 0.67;
    kmGroup.add(stake);

    const kmTex = createDistanceMarkerTexture(b.km, maxAnisotropy);
    const kmBoard = new THREE.Mesh(
      new THREE.BoxGeometry(1.45, 0.82, 0.1),
      new THREE.MeshStandardMaterial({
        map: kmTex,
        emissive: 0xffffff,
        emissiveMap: kmTex,
        emissiveIntensity: 0.22,
        roughness: 0.4,
      })
    );
    kmBoard.position.y = 1.48;
    kmGroup.add(kmBoard);
    orientAlongCurve(kmGroup, b.t - 0.025, b.side * 5.6, true);
    scene.add(kmGroup);

    // Feature Billboard slightly back on the grassy shoulder
    const bb = createTrackBillboard(b.title, b.sub, maxAnisotropy);
    orientAlongCurve(bb, b.t + 0.01, b.side * 9.8, true);
    scene.add(bb);
  });

  // Trackside Warm Streetlamps alternating sides
  for (let i = 0; i < 16; i++) {
    const t = 0.04 + (i / 15) * 0.91;
    const side = i % 2 === 0 ? -1 : 1;
    const lamp = createLampPost(side);
    orientAlongCurve(lamp, t, side * 5.8, false);
    scene.add(lamp);
  }

  // Cheering Colorful Crowd along both sides (Instanced composite body + head + raised cheering arms)
  const crowdCount = 190;
  const bodyGeo = new THREE.CapsuleGeometry(0.24, 0.62, 4, 8);
  bodyGeo.translate(0, 0.56, 0);
  const headGeo = new THREE.SphereGeometry(0.21, 10, 8);
  headGeo.translate(0, 1.24, 0);

  const crowdBodyMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.55,
    metalness: 0.08,
  });
  const crowdHeadMat = new THREE.MeshStandardMaterial({
    color: 0xf4c39b,
    roughness: 0.68,
  });

  const crowdBodies = new THREE.InstancedMesh(bodyGeo, crowdBodyMat, crowdCount);
  const crowdHeads = new THREE.InstancedMesh(headGeo, crowdHeadMat, crowdCount);
  crowdBodies.frustumCulled = false;
  crowdHeads.frustumCulled = false;

  const jerseyPalette = [
    new THREE.Color(0xd4ff2b), // acid lime
    new THREE.Color(0xee5a3a), // terracotta coral
    new THREE.Color(0x38bdf8), // sky blue
    new THREE.Color(0xfbbf24), // warm gold
    new THREE.Color(0x22c55e), // emerald mint
    new THREE.Color(0xa78bfa), // soft violet
    new THREE.Color(0xf5f5ee), // chalk white
  ];
  const skinPalette = [
    new THREE.Color(0xf5c8a4),
    new THREE.Color(0xd99b72),
    new THREE.Color(0x9a6342),
    new THREE.Color(0xfce0c8),
  ];

  const crowdMeta = [];
  const _dummy = new THREE.Object3D();

  for (let i = 0; i < crowdCount; i++) {
    const t = 0.03 + ((i % 95) / 95) * 0.92 + (Math.random() - 0.5) * 0.008;
    const clampedT = THREE.MathUtils.clamp(t, 0.015, 0.975);
    const side = i < crowdCount / 2 ? -1 : 1;
    const rowDepth = 5.4 + Math.random() * 2.8;

    trackCurve.getPointAt(clampedT, _pt);
    trackCurve.getTangentAt(clampedT, _tan).normalize();
    _right.crossVectors(_tan, _up).normalize();

    const x = _pt.x + _right.x * side * rowDepth;
    const z = _pt.z + _right.z * side * rowDepth;
    const scaleY = 0.88 + Math.random() * 0.28;
    const phase = Math.random() * Math.PI * 2;

    crowdMeta.push({
      t: clampedT,
      x,
      y: _pt.y,
      z,
      scaleY,
      phase,
      rotY: Math.atan2(-side * _right.x, -side * _right.z),
    });

    _dummy.position.set(x, _pt.y, z);
    _dummy.rotation.set(0, crowdMeta[i].rotY, 0);
    _dummy.scale.set(1, scaleY, 1);
    _dummy.updateMatrix();
    crowdBodies.setMatrixAt(i, _dummy.matrix);
    crowdHeads.setMatrixAt(i, _dummy.matrix);

    crowdBodies.setColorAt(
      i,
      jerseyPalette[Math.floor(Math.random() * jerseyPalette.length)]
    );
    crowdHeads.setColorAt(
      i,
      skinPalette[Math.floor(Math.random() * skinPalette.length)]
    );
  }
  crowdBodies.instanceMatrix.needsUpdate = true;
  crowdHeads.instanceMatrix.needsUpdate = true;
  if (crowdBodies.instanceColor) crowdBodies.instanceColor.needsUpdate = true;
  if (crowdHeads.instanceColor) crowdHeads.instanceColor.needsUpdate = true;
  scene.add(crowdBodies, crowdHeads);

  // Low-Poly Faceted Pine Trees (Composite InstancedMesh: trunk + 2 stacked faceted foliage tiers)
  const treeCount = 135;
  const trunkGeo = new THREE.CylinderGeometry(0.18, 0.28, 1.3, 6);
  trunkGeo.translate(0, 0.65, 0);
  const foliageLowerGeo = new THREE.ConeGeometry(1.35, 2.8, 6);
  foliageLowerGeo.translate(0, 2.4, 0);
  const foliageUpperGeo = new THREE.ConeGeometry(0.95, 2.2, 6);
  foliageUpperGeo.translate(0, 3.9, 0);

  const trunkMat = new THREE.MeshStandardMaterial({
    color: 0x3b2c22,
    roughness: 0.9,
    flatShading: true,
  });
  const foliageMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.78,
    metalness: 0.02,
    flatShading: true,
  });

  const treeTrunks = new THREE.InstancedMesh(trunkGeo, trunkMat, treeCount);
  const treeLower = new THREE.InstancedMesh(foliageLowerGeo, foliageMat, treeCount);
  const treeUpper = new THREE.InstancedMesh(foliageUpperGeo, foliageMat, treeCount);

  const treeGreens = [
    new THREE.Color(0x213d26),
    new THREE.Color(0x2d4f2c),
    new THREE.Color(0x1b3321),
    new THREE.Color(0x34592c),
  ];

  for (let i = 0; i < treeCount; i++) {
    const t = Math.random();
    const side = i % 2 === 0 ? -1 : 1;
    const dist = 10.5 + Math.random() * 26;

    trackCurve.getPointAt(t, _pt);
    trackCurve.getTangentAt(t, _tan).normalize();
    _right.crossVectors(_tan, _up).normalize();

    const s = 0.85 + Math.random() * 0.65; // ±15%+ organic scale variation
    _dummy.position.set(
      _pt.x + _right.x * side * dist,
      _pt.y - 0.1,
      _pt.z + _right.z * side * dist
    );
    _dummy.rotation.set(0, Math.random() * Math.PI * 2, 0);
    _dummy.scale.set(s, s * (0.92 + Math.random() * 0.25), s);
    _dummy.updateMatrix();

    treeTrunks.setMatrixAt(i, _dummy.matrix);
    treeLower.setMatrixAt(i, _dummy.matrix);
    treeUpper.setMatrixAt(i, _dummy.matrix);

    const col = treeGreens[Math.floor(Math.random() * treeGreens.length)];
    treeLower.setColorAt(i, col);
    treeUpper.setColorAt(i, col.clone().multiplyScalar(1.16));
  }
  treeTrunks.computeBoundingSphere();
  treeLower.computeBoundingSphere();
  treeUpper.computeBoundingSphere();
  scene.add(treeTrunks, treeLower, treeUpper);

  // Glowing Night City Skyline along outer horizon (composite towers with procedural window textures)
  const windowTex = createBuildingWindowTexture(maxAnisotropy);
  const towerMat = new THREE.MeshStandardMaterial({
    map: windowTex,
    emissive: 0xffdf99,
    emissiveMap: windowTex,
    emissiveIntensity: 0.55,
    roughness: 0.72,
    metalness: 0.25,
  });
  const roofMat = new THREE.MeshStandardMaterial({
    color: 0x161d1a,
    roughness: 0.6,
    metalness: 0.4,
  });
  const beaconMat = new THREE.MeshBasicMaterial({ color: 0xd4ff2b });

  for (let i = 0; i < 34; i++) {
    const t = i / 33;
    const side = i % 2 === 0 ? -1 : 1;
    const dist = 34 + Math.random() * 24;

    trackCurve.getPointAt(t, _pt);
    trackCurve.getTangentAt(t, _tan).normalize();
    _right.crossVectors(_tan, _up).normalize();

    const bGroup = new THREE.Group();
    const w = 5.5 + Math.random() * 6;
    const d = 5.5 + Math.random() * 6;
    const h = 16 + Math.random() * 34;

    const mainTower = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), towerMat);
    mainTower.position.y = h * 0.5;
    bGroup.add(mainTower);

    const penthouse = new THREE.Mesh(
      new THREE.BoxGeometry(w * 0.62, 2.4, d * 0.62),
      roofMat
    );
    penthouse.position.y = h + 1.2;
    bGroup.add(penthouse);

    if (i % 3 === 0) {
      const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 8), beaconMat);
      beacon.position.y = h + 3.2;
      bGroup.add(beacon);
    }

    bGroup.position.set(
      _pt.x + _right.x * side * dist,
      -0.5,
      _pt.z + _right.z * side * dist
    );
    scene.add(bGroup);
  }

  // Composite Animated 3D Runner Pacemaker
  const runner = createRunnerFigure();
  scene.add(runner);

  // Kinetic Acid-Lime Spark Trail Particles behind runner
  const sparkCount = 48;
  const sparkPositions = new Float32Array(sparkCount * 3);
  const sparkLife = new Float32Array(sparkCount);
  const sparkVel = Array.from({ length: sparkCount }, () => new THREE.Vector3());
  const sparkGeo = new THREE.BufferGeometry();
  sparkGeo.setAttribute("position", new THREE.BufferAttribute(sparkPositions, 3));
  const sparkMat = new THREE.PointsMaterial({
    color: 0xd4ff2b,
    size: 0.34,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
  });
  const sparks = new THREE.Points(sparkGeo, sparkMat);
  sparks.frustumCulled = false;
  scene.add(sparks);

  // Pre-warm shaders once on GPU
  if (!isSoftwareGl) {
    renderer.compile(scene, camera);
  }

  // State & Kinematics (all pre-allocated math helpers outside render loop)
  const startT = mode === "dashboard" ? Math.min(0.86, Math.max(0.06, initialProgress * 0.82)) : 0.035;
  let progressT = startT;
  let targetT = startT;
  let velocity = 0;
  let isHoldingForward = false;
  let isHoldingBack = false;
  let autoTargetT = null;
  let elapsedRunSec = 0;
  let footstepAccum = 0;
  let lastStageIdx = -1;
  let pointerOffsetX = 0;
  let pointerOffsetY = 0;

  const _runnerPos = new THREE.Vector3();
  const _runnerTan = new THREE.Vector3();
  const _camTargetPos = new THREE.Vector3();
  const _camLookAt = new THREE.Vector3();
  const _rightVec = new THREE.Vector3();

  // HUD DOM elements (optional depending on mode)
  const hudStageNum = container.querySelector("[data-hud-stage-num]");
  const hudStageLabel = container.querySelector("[data-hud-stage-label]");
  const hudKm = container.querySelector("[data-hud-km]");
  const hudPace = container.querySelector("[data-hud-pace]");
  const hudTime = container.querySelector("[data-hud-time]");
  const hudSplineDot = container.querySelector("[data-hud-spline-dot]");
  const hudSplinePath = container.querySelector("[data-hud-spline-path]");
  const hudStageTitle = container.querySelector("[data-stage-title]");
  const hudStageBody = container.querySelector("[data-stage-body]");
  const hudStageMeta = container.querySelector("[data-stage-meta]");
  const hudStageAction = container.querySelector("[data-stage-action]");
  const mapButtons = container.querySelectorAll("[data-jump-stage]");

  function updateStageHUD(t, currentSpeed) {
    // Distance 0.000 -> 7.000 KM
    const km = Math.max(0, ((t - 0.035) / 0.905) * 7.0);
    if (hudKm) hudKm.textContent = km.toFixed(3).padStart(6, "0");

    if (hudPace) {
      if (currentSpeed > 0.008) {
        const paceMin = THREE.MathUtils.clamp(6.4 - currentSpeed * 28, 2.8, 7.5);
        const mins = Math.floor(paceMin);
        const secs = Math.floor((paceMin - mins) * 60);
        hudPace.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      } else {
        hudPace.textContent = "--:--";
      }
    }

    if (hudTime) {
      const m = Math.floor(elapsedRunSec / 60);
      const s = Math.floor(elapsedRunSec % 60);
      hudTime.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    // Move SVG minimap dot along path
    if (hudSplinePath && hudSplineDot && typeof hudSplinePath.getTotalLength === "function") {
      const totalLen = hudSplinePath.getTotalLength();
      const norm = THREE.MathUtils.clamp((t - 0.035) / 0.905, 0, 1);
      const pt = hudSplinePath.getPointAtLength(norm * totalLen);
      hudSplineDot.setAttribute("cx", pt.x.toFixed(1));
      hudSplineDot.setAttribute("cy", pt.y.toFixed(1));
    }

    // Determine active stage (0..stages.length-1)
    if (stages.length > 0) {
      const norm = THREE.MathUtils.clamp((t - 0.035) / 0.905, 0, 0.9999);
      const stageIdx = Math.min(stages.length - 1, Math.floor(norm * stages.length));
      if (stageIdx !== lastStageIdx) {
        const prevIdx = lastStageIdx;
        lastStageIdx = stageIdx;
        const stage = stages[stageIdx];
        if (hudStageNum) {
          hudStageNum.textContent = `${String(stageIdx + 1).padStart(2, "0")}/${String(stages.length).padStart(2, "0")}`;
        }
        if (hudStageLabel) hudStageLabel.textContent = stage.shortLabel || stage.title;
        if (hudStageTitle) hudStageTitle.textContent = stage.title;
        if (hudStageBody) hudStageBody.textContent = stage.body;
        if (hudStageMeta) hudStageMeta.textContent = stage.meta;
        if (hudStageAction && stage.ctaText && stage.ctaHref) {
          hudStageAction.textContent = stage.ctaText;
          hudStageAction.setAttribute("href", stage.ctaHref);
        }
        mapButtons.forEach((btn) => {
          const idx = parseInt(btn.getAttribute("data-jump-stage") || "-1", 10);
          btn.classList.toggle("active", idx === stageIdx);
        });
        if (prevIdx !== -1 && window.FitTrackSound) {
          window.FitTrackSound.playStagePass(stageIdx);
          if (stageIdx === stages.length - 1) {
            window.FitTrackSound.playCrowdCheer();
          }
        }
      }
    }
  }

  // Interactive Controls: Wheel, Space / ArrowUp / ArrowDown, Hold RUN button, Course Map jump
  function handleWheel(e) {
    if (mode !== "landing") return;
    // Allow normal vertical page scroll if user is past the finish line scrolling down,
    // or at the very start scrolling up
    const scrollingDown = e.deltaY > 0;
    if (scrollingDown && targetT >= 0.935) return;
    if (!scrollingDown && targetT <= 0.036 && window.scrollY <= 5) return;

    // Only hijack scroll when the 3D stage is prominently in viewport
    const rect = container.getBoundingClientRect();
    if (rect.top < -80 || rect.bottom < window.innerHeight * 0.45) return;

    e.preventDefault();
    autoTargetT = null;
    const step = THREE.MathUtils.clamp(e.deltaY * 0.00028, -0.055, 0.055);
    targetT = THREE.MathUtils.clamp(targetT + step, 0.035, 0.94);
  }

  function isTypingInField(el) {
    if (!el) return false;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
  }

  function handleKeyDown(e) {
    if (isTypingInField(document.activeElement)) return;
    if (e.code === "Space" || e.code === "ArrowUp") {
      const rect = container.getBoundingClientRect();
      if (rect.bottom > 80 && rect.top < window.innerHeight - 60) {
        e.preventDefault();
        autoTargetT = null;
        isHoldingForward = true;
      }
    } else if (e.code === "ArrowDown") {
      const rect = container.getBoundingClientRect();
      if (rect.bottom > 80 && rect.top < window.innerHeight - 60) {
        e.preventDefault();
        autoTargetT = null;
        isHoldingBack = true;
      }
    } else if (e.key === "h" || e.key === "H") {
      const dock = container.querySelector("[data-hud-dock]");
      if (dock) dock.classList.toggle("is-collapsed");
    }
  }

  function handleKeyUp(e) {
    if (e.code === "Space" || e.code === "ArrowUp") {
      isHoldingForward = false;
    } else if (e.code === "ArrowDown") {
      isHoldingBack = false;
    }
  }

  function handlePointerMove(e) {
    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    pointerOffsetX = THREE.MathUtils.clamp(nx, -1, 1);
    pointerOffsetY = THREE.MathUtils.clamp(ny, -1, 1);
  }

  container.addEventListener("wheel", handleWheel, { passive: false });
  container.addEventListener("pointermove", handlePointerMove, { passive: true });
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("keyup", handleKeyUp);

  // Hold-to-run buttons inside stage
  container.querySelectorAll("[data-hold-run]").forEach((btn) => {
    const startHold = (e) => {
      e.preventDefault();
      autoTargetT = null;
      isHoldingForward = true;
      btn.classList.add("is-pressing");
      if (window.FitTrackSound && progressT < 0.06) {
        window.FitTrackSound.playCountdownBeep(true);
      }
    };
    const endHold = () => {
      isHoldingForward = false;
      btn.classList.remove("is-pressing");
    };
    btn.addEventListener("pointerdown", startHold);
    btn.addEventListener("pointerup", endHold);
    btn.addEventListener("pointerleave", endHold);
    btn.addEventListener("pointercancel", endHold);
  });

  // Course map checkpoint jumps
  mapButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-jump-stage") || "0", 10);
      const count = Math.max(1, stages.length);
      const dest = 0.035 + (idx / Math.max(1, count - 1)) * 0.905;
      autoTargetT = THREE.MathUtils.clamp(dest, 0.035, 0.94);
      targetT = autoTargetT;
      if (window.FitTrackSound) window.FitTrackSound.playClick();
      const drawer = container.querySelector("[data-course-map-drawer]");
      if (drawer) drawer.classList.remove("is-open");
    });
  });

  // Course map drawer open/close
  const mapDrawer = container.querySelector("[data-course-map-drawer]");
  container.querySelectorAll("[data-course-map-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!mapDrawer) return;
      mapDrawer.classList.toggle("is-open");
      if (window.FitTrackSound) window.FitTrackSound.playClick();
    });
  });

  // HUD collapse toggle
  const hudDock = container.querySelector("[data-hud-dock]");
  const hudToggle = container.querySelector("[data-hud-collapse-toggle]");
  if (hudDock && hudToggle) {
    hudToggle.addEventListener("click", () => {
      const collapsed = hudDock.classList.toggle("is-collapsed");
      hudToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      const txt = hudToggle.querySelector("span");
      if (txt) txt.textContent = collapsed ? "Show Telemetry" : "Hide HUD";
      if (window.FitTrackSound) window.FitTrackSound.playClick();
    });
  }

  // Resize observer
  function onResize() {
    const w = mountEl.clientWidth || window.innerWidth;
    const h = mountEl.clientHeight || 540;
    camera.aspect = w / Math.max(1, h);
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  const resizeObs = new ResizeObserver(onResize);
  resizeObs.observe(mountEl);

  // WebGL context loss/restore safety
  let contextLost = false;
  renderer.domElement.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    contextLost = true;
  });
  renderer.domElement.addEventListener("webglcontextrestored", () => {
    contextLost = false;
  });

  // Animation loop with software WebGL fenceSync afterDraw pacing
  const clock = new THREE.Clock();
  let frameId = 0;
  let disposed = false;

  function afterDraw(cb) {
    const gl = renderer.getContext();
    if (gl && typeof gl.fenceSync === "function") {
      const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
      gl.flush();
      const poll = () => {
        if (disposed) return;
        const state = sync && gl.getSyncParameter(sync, gl.SYNC_STATUS);
        if (state === gl.UNSIGNALED) {
          frameId = window.setTimeout(poll, 5);
        } else {
          if (sync) gl.deleteSync(sync);
          frameId = window.setTimeout(cb, 80);
        }
      };
      frameId = window.setTimeout(poll, 5);
    } else {
      frameId = window.setTimeout(cb, 90);
    }
  }

  function tick() {
    if (disposed) return;
    if (contextLost) {
      frameId = window.setTimeout(tick, 200);
      return;
    }

    const dt = Math.min(clock.getDelta(), 0.08);
    const elapsed = clock.getElapsedTime();

    // Update targetT from held keys or dashboard gentle loop
    if (isHoldingForward) {
      targetT += dt * (mode === "dashboard" ? 0.14 : 0.11);
      if (mode === "dashboard" && targetT > 0.92) {
        targetT = 0.04;
        progressT = 0.04;
      } else {
        targetT = Math.min(0.94, targetT);
      }
    } else if (isHoldingBack) {
      targetT = Math.max(0.035, targetT - dt * 0.09);
    } else if (mode === "dashboard" && !prefersReducedMotion) {
      // Gentle scenic jog pacing on dashboard arena
      targetT += dt * 0.018;
      if (targetT > 0.91) {
        targetT = 0.04;
        progressT = 0.04;
      }
    }

    const prevT = progressT;
    const dampSpeed = autoTargetT !== null ? 4.2 : 5.5;
    progressT = THREE.MathUtils.damp(progressT, targetT, dampSpeed, dt);
    if (autoTargetT !== null && Math.abs(progressT - autoTargetT) < 0.002) {
      autoTargetT = null;
    }

    const instantSpeed = Math.abs(progressT - prevT) / Math.max(0.001, dt);
    velocity = THREE.MathUtils.damp(velocity, instantSpeed, 6, dt);

    if (velocity > 0.005) {
      elapsedRunSec += dt;
      footstepAccum += dt * (2.6 + velocity * 28);
      if (footstepAccum >= 1) {
        footstepAccum = 0;
        if (window.FitTrackSound && velocity > 0.02) {
          window.FitTrackSound.playFootstep(Math.min(1, velocity * 8));
        }
      }
    }

    // Position 3D Runner slightly ahead of camera on lane 3
    const runnerT = THREE.MathUtils.clamp(progressT + 0.022, 0.02, 0.975);
    trackCurve.getPointAt(runnerT, _runnerPos);
    trackCurve.getTangentAt(runnerT, _runnerTan).normalize();
    _rightVec.crossVectors(_runnerTan, _up).normalize();

    runner.position.copy(_runnerPos);
    runner.position.y += 0.05;
    runner.rotation.y = Math.atan2(_runnerTan.x, _runnerTan.z);

    // Animate runner stride limbs + athletic bobbing
    const strideFreq = prefersReducedMotion ? 0 : 4.5 + velocity * 55;
    const strideAmp = prefersReducedMotion ? 0 : THREE.MathUtils.clamp(0.18 + velocity * 6.5, 0.16, 0.95);
    const stridePhase = elapsed * strideFreq;

    const rd = runner.userData;
    rd.leftLegPivot.rotation.x = Math.sin(stridePhase) * strideAmp;
    rd.rightLegPivot.rotation.x = -Math.sin(stridePhase) * strideAmp;
    rd.leftArmPivot.rotation.x = -Math.sin(stridePhase) * strideAmp * 0.9;
    rd.rightArmPivot.rotation.x = Math.sin(stridePhase) * strideAmp * 0.9;
    rd.body.position.y = Math.abs(Math.cos(stridePhase)) * (0.04 + velocity * 1.1);
    rd.body.rotation.x = THREE.MathUtils.clamp(velocity * 2.2, 0.04, 0.28);
    rd.glowRing.scale.setScalar(1 + Math.sin(elapsed * 5) * 0.08 + velocity * 2.2);

    runnerGlowLight.position.set(_runnerPos.x, _runnerPos.y + 1.8, _runnerPos.z);

    // Update kinetic lime spark trail behind runner
    const sparkAttr = sparkGeo.attributes.position;
    for (let i = 0; i < sparkCount; i++) {
      sparkLife[i] -= dt * (1.2 + velocity * 12);
      if (sparkLife[i] <= 0) {
        sparkLife[i] = 0.4 + Math.random() * 0.8;
        sparkAttr.setXYZ(
          i,
          _runnerPos.x + (Math.random() - 0.5) * 0.7,
          _runnerPos.y + 0.12 + Math.random() * 0.35,
          _runnerPos.z + (Math.random() - 0.5) * 0.7
        );
        sparkVel[i].set(
          -_runnerTan.x * (1.2 + velocity * 14) + (Math.random() - 0.5) * 0.9,
          0.6 + Math.random() * 1.3,
          -_runnerTan.z * (1.2 + velocity * 14) + (Math.random() - 0.5) * 0.9
        );
      } else {
        sparkAttr.setXYZ(
          i,
          sparkAttr.getX(i) + sparkVel[i].x * dt,
          sparkAttr.getY(i) + sparkVel[i].y * dt,
          sparkAttr.getZ(i) + sparkVel[i].z * dt
        );
      }
    }
    sparkAttr.needsUpdate = true;

    // Animate cheering spectators near the runner (Mexican wave jump!)
    if (!prefersReducedMotion) {
      for (let i = 0; i < crowdCount; i++) {
        const cm = crowdMeta[i];
        const proximity = Math.max(0, 1 - Math.abs(cm.t - runnerT) * 14);
        const hopAmp = 0.06 + proximity * (0.42 + Math.min(0.3, velocity * 3));
        const hop = Math.abs(Math.sin(elapsed * (3.5 + proximity * 5) + cm.phase)) * hopAmp;
        _dummy.position.set(cm.x, cm.y + hop, cm.z);
        _dummy.rotation.set(0, cm.rotY, Math.sin(elapsed * 5 + cm.phase) * proximity * 0.14);
        _dummy.scale.set(1, cm.scaleY + hop * 0.12, 1);
        _dummy.updateMatrix();
        crowdBodies.setMatrixAt(i, _dummy.matrix);
        crowdHeads.setMatrixAt(i, _dummy.matrix);
      }
      crowdBodies.instanceMatrix.needsUpdate = true;
      crowdHeads.instanceMatrix.needsUpdate = true;
    }

    // Animate START gantry countdown lights smoothly (gentle chase pulse)
    if (startGantry.userData.raceLights) {
      startGantry.userData.raceLights.forEach((mat, idx) => {
        const pulse = 0.9 + 0.75 * Math.sin(elapsed * 3.4 - idx * 0.85);
        mat.emissiveIntensity = pulse;
      });
    }

    // Smooth Chase Camera Positioning + Subtle Mouse Parallax + Speed FOV Widening
    trackCurve.getPointAt(progressT, _camTargetPos);
    trackCurve.getTangentAt(progressT, _tan).normalize();
    _rightVec.crossVectors(_tan, _up).normalize();

    const camHeight = mode === "dashboard" ? 3.2 : 3.55;
    const camBack = mode === "dashboard" ? 4.4 : 4.8;
    const lateralSway = pointerOffsetX * 1.15;

    _camTargetPos.addScaledVector(_tan, -camBack);
    _camTargetPos.addScaledVector(_rightVec, lateralSway + (mode === "landing" ? -0.9 : 0));
    _camTargetPos.y += camHeight - pointerOffsetY * 0.35;

    camera.position.x = THREE.MathUtils.damp(camera.position.x, _camTargetPos.x, 7, dt);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, _camTargetPos.y, 7, dt);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, _camTargetPos.z, 7, dt);

    const lookT = THREE.MathUtils.clamp(progressT + 0.085, 0.05, 0.99);
    trackCurve.getPointAt(lookT, _camLookAt);
    _camLookAt.y += 1.65;
    camera.lookAt(_camLookAt);

    // Dynamic FOV widening on sprints
    const targetFov = baseFov + THREE.MathUtils.clamp(velocity * 72, 0, 9.5);
    if (Math.abs(camera.fov - targetFov) > 0.05) {
      camera.fov = THREE.MathUtils.damp(camera.fov, targetFov, 5, dt);
      camera.updateProjectionMatrix();
    }

    // Update live HUD telemetry
    updateStageHUD(progressT, velocity);

    renderer.render(scene, camera);

    if (isSoftwareGl) {
      afterDraw(tick);
    } else {
      frameId = requestAnimationFrame(tick);
    }
  }

  // Initialize camera immediately at starting position so first frame is never blank
  trackCurve.getPointAt(progressT, _camTargetPos);
  trackCurve.getTangentAt(progressT, _tan).normalize();
  camera.position.set(_camTargetPos.x - 0.9, _camTargetPos.y + 3.55, _camTargetPos.z + 4.8);
  trackCurve.getPointAt(THREE.MathUtils.clamp(progressT + 0.085, 0.05, 0.99), _camLookAt);
  _camLookAt.y += 1.65;
  camera.lookAt(_camLookAt);
  updateStageHUD(progressT, 0);

  tick();

  return {
    jumpToNormalized(norm) {
      autoTargetT = THREE.MathUtils.clamp(0.035 + norm * 0.905, 0.035, 0.94);
      targetT = autoTargetT;
    },
    triggerBoost() {
      autoTargetT = null;
      targetT = Math.min(0.92, progressT + 0.14);
      if (window.FitTrackSound) window.FitTrackSound.playCrowdCheer();
    },
    dispose() {
      disposed = true;
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      resizeObs.disconnect();
      container.removeEventListener("wheel", handleWheel);
      container.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      renderer.dispose();
    },
  };
}

// Auto-mount any 3D stage elements present on the page
document.addEventListener("DOMContentLoaded", () => {
  const landingStage = document.getElementById("fittrack3DLandingStage");
  if (landingStage) {
    const stagesScript = document.getElementById("landing-track-stages-json");
    let stages = [];
    if (stagesScript) {
      try {
        stages = JSON.parse(stagesScript.textContent || "[]");
      } catch (_) {}
    }
    window.__fittrackLanding3D = initFitTrack3D(landingStage, {
      mode: "landing",
      stages,
    });
  }

  const dashStage = document.getElementById("dashboard3DTrackStage");
  if (dashStage) {
    const initialProgress = parseFloat(
      dashStage.getAttribute("data-progress") || "0.18"
    );
    const controller = initFitTrack3D(dashStage, {
      mode: "dashboard",
      initialProgress: isNaN(initialProgress) ? 0.18 : initialProgress,
    });
    window.__fittrackDashboard3D = controller;

    const boostBtn = document.getElementById("dashboardSprintBoostBtn");
    if (boostBtn && controller) {
      boostBtn.addEventListener("click", () => {
        controller.triggerBoost();
      });
    }
  }
});
