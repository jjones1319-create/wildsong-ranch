import { BackSide, Color, FrontSide, NoColorSpace, ShaderMaterial, Texture, Vector2, Vector3, Vector4, type Matrix4 } from 'three'
import { ART } from '../data/tuning.ts'

/**
 * The cel shader (ART_2_PLAN §2.1, §3.2): two tones with a soft terminator, shadows as the local colour shifted
 * cooler and darker, a warm rim on the dark side, the sick tint and the old fade; the inverted-hull outline in a
 * darker tint of the colour beneath; and the face material that shows one cell of the Blender face sheet and
 * decodes the pupil masks. One program each, shared by every monster.
 */

export type LightPreset = keyof typeof ART.light

export interface LightRig {
  key: Color
  fill: Color
  rim: Color
  /** World-space direction toward the key light (three's Y-up). */
  dir: Vector3
}

export function lightRig(preset: LightPreset): LightRig {
  const p = ART.light[preset]
  return { key: new Color(p.key), fill: new Color(p.fill), rim: new Color(p.rim), dir: new Vector3(...p.dir).normalize() }
}

const SKIN_VERTEX = /* glsl */ `
#include <common>
#include <skinning_pars_vertex>
varying vec3 vNormal;
varying vec2 vUv;
varying vec3 vViewDir;
void main() {
  vUv = uv;
  #include <beginnormal_vertex>
  #include <skinbase_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  vNormal = normalize(transformedNormal);
  vViewDir = -mvPosition.xyz;
}
`

const TOON_FRAGMENT = /* glsl */ `
uniform sampler2D map;
uniform vec3 keyDir;
uniform vec3 keyColor;
uniform vec3 fillColor;
uniform vec3 rimColor;
uniform float terminator;
uniform float softness;
uniform vec3 shadowMul;
uniform float rimPower;
uniform float rimStrength;
uniform float fillStrength;
uniform vec3 sickTint;
uniform float sickMix;
uniform float oldDesat;
uniform float oldMix;
uniform float flash;
uniform float opacity;
varying vec3 vNormal;
varying vec2 vUv;
varying vec3 vViewDir;
void main() {
  vec4 tex = texture2D(map, vUv);
  vec3 albedo = tex.rgb;
  albedo = mix(albedo, albedo * sickTint, sickMix);
  float lum = dot(albedo, vec3(0.299, 0.587, 0.114));
  albedo = mix(albedo, mix(albedo, vec3(lum), oldDesat) * 0.92, oldMix);
  vec3 n = normalize(vNormal);
  vec3 l = normalize(keyDir);
  float ndl = dot(n, l);
  float lit = smoothstep(terminator - softness, terminator + softness, ndl);
  vec3 shadowCol = albedo * shadowMul;
  vec3 litCol = albedo * keyColor;
  vec3 col = mix(shadowCol, litCol, lit);
  float fillK = clamp(dot(n, -l) * 0.5 + 0.5, 0.0, 1.0) * fillStrength * (1.0 - lit);
  col += albedo * fillColor * fillK;
  vec3 v = normalize(vViewDir);
  float fres = pow(1.0 - max(dot(n, v), 0.0), rimPower);
  col += rimColor * fres * rimStrength * (1.0 - lit);
  col = mix(col, vec3(1.0), flash);
  gl_FragColor = vec4(col, opacity * tex.a);
  #include <colorspace_fragment>
}
`

const OUTLINE_VERTEX = /* glsl */ `
#include <common>
#include <skinning_pars_vertex>
uniform float outlinePx;
uniform vec2 resolution;
varying vec2 vUv;
void main() {
  vUv = uv;
  #include <beginnormal_vertex>
  #include <skinbase_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  // three flips transformedNormal for BackSide materials (FLIP_SIDED); the hull must push outward, so use the
  // skinned object normal straight through the normal matrix.
  vec3 outward = normalize(normalMatrix * objectNormal);
  vec4 clipN = projectionMatrix * vec4(outward, 0.0);
  vec2 dir = clipN.xy;
  float len = length(dir);
  dir = len > 1e-5 ? dir / len : vec2(0.0);
  gl_Position.xy += dir * (outlinePx * 2.0 / resolution) * gl_Position.w;
}
`

const OUTLINE_FRAGMENT = /* glsl */ `
uniform vec3 outlineColor;
uniform float opacity;
varying vec2 vUv;
void main() {
  gl_FragColor = vec4(outlineColor, opacity);
  #include <colorspace_fragment>
}
`

const FACE_FRAGMENT = /* glsl */ `
uniform sampler2D sheet;
uniform vec4 cell;
uniform float mirror;
uniform vec2 pupilOffset;
uniform float pupilScale;
uniform float isPupil;
uniform vec3 irisColor;
uniform vec3 pupilColor;
uniform vec3 keyDir;
uniform float shade;
uniform float flash;
uniform float opacity;
varying vec3 vNormal;
varying vec2 vUv;
void main() {
  vec2 p = vUv;
  if (mirror > 0.5) p.x = 1.0 - p.x;
  if (isPupil > 0.5) p = (p - 0.5) / pupilScale + 0.5 - pupilOffset;
  if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0) discard;
  vec2 suv = cell.xy + p * cell.zw;
  vec4 t = texture2D(sheet, suv);
  vec3 col;
  float a;
  if (isPupil > 0.5) {
    vec3 iris = irisColor * (0.7 + 0.55 * p.y);
    col = mix(iris, pupilColor, t.g);
    col = mix(col, vec3(1.0), t.b);
    a = max(t.r, max(t.g, t.b));
  } else {
    col = t.rgb;
    a = t.a;
  }
  float ndl = dot(normalize(vNormal), normalize(keyDir));
  float lit = smoothstep(-0.25, 0.35, ndl);
  col *= mix(1.0, 0.8 + 0.2 * lit, shade);
  col = mix(col, vec3(1.0), flash);
  if (a < 0.01) discard;
  gl_FragColor = vec4(col, a * opacity);
  #include <colorspace_fragment>
}
`

export function makeToonMaterial(map: Texture): ShaderMaterial {
  const t = ART.toon
  return new ShaderMaterial({
    vertexShader: SKIN_VERTEX,
    fragmentShader: TOON_FRAGMENT,
    uniforms: {
      map: { value: map },
      keyDir: { value: new Vector3(0.4, 0.8, 0.5) },
      keyColor: { value: new Color('#ffffff') },
      fillColor: { value: new Color('#cfe3ff') },
      rimColor: { value: new Color('#ffd9b0') },
      terminator: { value: t.terminator },
      softness: { value: t.softness },
      shadowMul: { value: new Vector3(...t.shadowMul) },
      rimPower: { value: t.rimPower },
      rimStrength: { value: t.rimStrength },
      fillStrength: { value: t.fillStrength },
      sickTint: { value: new Vector3(...t.sickTint) },
      sickMix: { value: 0 },
      oldDesat: { value: t.oldDesaturate },
      oldMix: { value: 0 },
      flash: { value: 0 },
      opacity: { value: 1 },
    },
    side: FrontSide,
  })
}

/** The outline is a darker, slightly cooler tint of the look's body colour (§2.1: never black). */
export function outlineColorFor(bodyHex: string): Color {
  const c = new Color(bodyHex)
  const m = ART.toon.outlineMul
  return c.setRGB(c.r * m[0], c.g * m[1], c.b * m[2])
}

export function makeOutlineMaterial(bodyHex: string, outlinePx: number): ShaderMaterial {
  return new ShaderMaterial({
    vertexShader: OUTLINE_VERTEX,
    fragmentShader: OUTLINE_FRAGMENT,
    uniforms: {
      outlinePx: { value: outlinePx },
      resolution: { value: new Vector2(360, 360) },
      outlineColor: { value: outlineColorFor(bodyHex) },
      opacity: { value: 1 },
    },
    side: BackSide,
  })
}

export function makeFaceMaterial(sheet: Texture, kind: 'white' | 'pupil' | 'lid' | 'mouth', eyeHex: string): ShaderMaterial {
  const pupil = kind === 'pupil'
  let tex = sheet
  if (pupil) {
    // the masks must not be colour-managed: a linear copy of the same image
    tex = sheet.clone()
    tex.colorSpace = NoColorSpace
    tex.needsUpdate = true
  }
  const iris = new Color(eyeHex)
  const dark = iris.clone().multiplyScalar(0.45)
  return new ShaderMaterial({
    vertexShader: SKIN_VERTEX,
    fragmentShader: FACE_FRAGMENT,
    uniforms: {
      sheet: { value: tex },
      cell: { value: new Vector4(0, 0, 0.25, 0.15625) },
      mirror: { value: 0 },
      pupilOffset: { value: new Vector2(0, 0) },
      pupilScale: { value: 1 },
      isPupil: { value: pupil ? 1 : 0 },
      irisColor: { value: iris },
      pupilColor: { value: dark },
      keyDir: { value: new Vector3(0.4, 0.8, 0.5) },
      shade: { value: kind === 'pupil' ? 0.3 : 0.7 },
      flash: { value: 0 },
      opacity: { value: 1 },
    },
    transparent: true,
    depthWrite: false,
    side: FrontSide,
    // the patches sit a few millimetres over the body; a depth offset keeps the body's bumps from poking through
    polygonOffset: true,
    polygonOffsetFactor: -3,
    polygonOffsetUnits: -6,
  })
}

const tmpDir = new Vector3()

/** Push the rig into a material, with the key direction in view space (the camera's matrixWorldInverse). */
export function applyLight(mat: ShaderMaterial, rig: LightRig, viewMatrix: Matrix4): void {
  const u = mat.uniforms
  if (u.keyDir) (u.keyDir.value as Vector3).copy(tmpDir.copy(rig.dir).transformDirection(viewMatrix))
  if (u.keyColor) (u.keyColor.value as Color).copy(rig.key)
  if (u.fillColor) (u.fillColor.value as Color).copy(rig.fill)
  if (u.rimColor) (u.rimColor.value as Color).copy(rig.rim)
}
