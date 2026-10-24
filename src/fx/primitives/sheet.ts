import { Mesh, MeshGeometry, Shader, type UniformGroup } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, SheetParams } from './types.ts'

/**
 * #9 sheet: a quad with a scrolling-noise shader: a falling water sheet (waterfall) or a wave that rises from the
 * floor and curls toward `dir`. The foam band sits where the noise is brightest; alpha fades at the edges.
 */
const VERT = /* glsl */ `
in vec2 aPosition;
in vec2 aUV;
out vec2 vUV;
uniform mat3 uProjectionMatrix;
uniform mat3 uWorldTransformMatrix;
uniform mat3 uTransformMatrix;
void main() {
  mat3 mvp = uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix;
  gl_Position = vec4((mvp * vec3(aPosition, 1.0)).xy, 0.0, 1.0);
  vUV = aUV;
}`

const FRAG = /* glsl */ `
precision mediump float;
in vec2 vUV;
out vec4 finalColor;
uniform float uTime;
uniform float uFoam;
uniform float uAlpha;
uniform float uRising;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorFoam;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
void main() {
  vec2 uv = vUV;
  // Falling sheet: long vertical streaks racing down. Rising wave: slower horizontal rolls.
  float flow = uRising > 0.5 ? uv.y + uTime * 0.8 : uv.y - uTime * 1.6;
  float n = uRising > 0.5
    ? noise(vec2(uv.x * 5.0 + uTime * 0.6, flow * 6.0)) * 0.6 + noise(vec2(uv.x * 11.0, flow * 13.0)) * 0.4
    : noise(vec2(uv.x * 16.0, flow * 3.0)) * 0.6 + noise(vec2(uv.x * 30.0 + 2.0, flow * 7.0)) * 0.4;
  // The wave's crest: a curled top edge that leans forward; the fall keeps a straight top.
  float crest = uRising > 0.5 ? 0.72 + 0.2 * sin(uv.x * 3.1416) + 0.05 * (n - 0.5) : 1.0;
  float body = uRising > 0.5 ? 1.0 - smoothstep(crest - 0.06, crest + 0.02, uv.y) : 1.0;
  vec3 col = mix(uColorB, uColorA, n);
  float foam = smoothstep(1.0 - uFoam - 0.1, 1.0 - uFoam + 0.08, n);
  // Foam along the leading edge (the crest of a wave, the bottom of a fall).
  float edge = uRising > 0.5 ? smoothstep(crest - 0.18, crest - 0.02, uv.y) : smoothstep(0.8, 1.0, 1.0 - uv.y);
  foam = max(foam, edge * (0.7 + 0.3 * n));
  col = mix(col, uColorFoam, foam);
  float side = smoothstep(0.0, 0.14, uv.x) * smoothstep(0.0, 0.14, 1.0 - uv.x);
  float base = uRising > 0.5 ? smoothstep(0.0, 0.08, uv.y) : 1.0;
  float a = (0.6 + 0.4 * n) * side * body * base * uAlpha;
  finalColor = vec4(col * a, a);
}`

function rgb(c: number): [number, number, number] {
  return [((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255]
}

export function sheet(ctx: FxContext, p: SheetParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const width = scaled(p.width ?? FX.sheet.width, str)
  const height = scaled(p.height ?? FX.sheet.height, str)
  const duration = p.durationMs ?? FX.sheet.durationMs
  const rising = p.rising ?? true
  const dir = p.dir ?? 1
  // Unit quad; the mesh is scaled to width × height each frame so a wave can grow.
  const geometry = new MeshGeometry({ positions: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), uvs: new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), indices: new Uint32Array([0, 1, 2, 0, 2, 3]) })
  const shader = Shader.from({
    gl: { vertex: VERT, fragment: FRAG, name: 'wildsong-sheet' },
    resources: {
      sheetUniforms: {
        uTime: { value: 0, type: 'f32' },
        uFoam: { value: FX.sheet.foam, type: 'f32' },
        uAlpha: { value: 0, type: 'f32' },
        uRising: { value: rising ? 1 : 0, type: 'f32' },
        uColorA: { value: rgb(style.ramp[1]!), type: 'vec3<f32>' },
        uColorB: { value: rgb(style.ramp[2]!), type: 'vec3<f32>' },
        uColorFoam: { value: rgb(style.core), type: 'vec3<f32>' },
      },
    },
  })
  const mesh = new Mesh({ geometry, shader })
  ctx.shapes.addChild(mesh)
  const uniforms = (shader.resources as Record<string, UniformGroup>).sheetUniforms!.uniforms as { uTime: number; uAlpha: number }
  let spray = 0
  return timed(
    duration,
    (prog, dt) => {
      uniforms.uTime += (dt / 1000) * FX.sheet.scroll
      const env = prog < 0.15 ? prog / 0.15 : prog > 0.7 ? (1 - prog) / 0.3 : 1
      uniforms.uAlpha = 0.95 * env
      if (rising) {
        // Grows up from the floor, leans and curls toward dir as it crests.
        const h = height * Math.min(1, prog / 0.45)
        mesh.scale.set(width, -h)
        mesh.skew.set(-dir * 0.35 * Math.min(1, prog / 0.6), 0)
        mesh.position.set(p.x - width / 2 + dir * width * 0.25 * prog, p.y)
      } else {
        mesh.scale.set(width, height)
        mesh.position.set(p.x - width / 2, p.y - height)
      }
      spray += dt
      if (spray > 45 && ctx.allowance(2) > 0) {
        spray = 0
        const top = rising ? p.y - height * Math.min(1, prog / 0.45) : p.y
        spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-width / 2, width / 2), y: top, vx: ctx.rng.range(-60, 60) + (rising ? dir * 120 : 0), vy: rising ? -ctx.rng.range(80, 220) : ctx.rng.range(20, 80), gravity: 700, drag: 0.9, lifeMs: 600, size0: 8, size1: 3, fadeFrom: 0.5 }, style)
      }
    },
    () => {
      mesh.destroy()
      shader.destroy()
      geometry.destroy()
    },
  )
}
