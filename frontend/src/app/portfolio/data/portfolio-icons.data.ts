/**
 * Catálogo curado de iconos del portafolio — usado por el sidebar
 * (socials + tech chips) y por el editor (dropdown / autocomplete).
 *
 * Diseño:
 * - Los SVGs de marcas conocidas vienen de `simple-icons` (CC0). Cada
 *   icono se importa individualmente para que tree-shaking bundle solo
 *   los que realmente exponemos.
 * - Algunas marcas fueron removidas de simple-icons por trademark
 *   (LinkedIn, CodePen, OpenAI, AWS, Java, C#). Para esas y para
 *   iconos genéricos (email, website, phone, rss) usamos SVG paths
 *   inline.
 * - Todos los paths asumen viewBox 24x24 y un único <path fill="currentColor">.
 *
 * Extender: para agregar un nuevo icono
 *   1. Si es marca conocida: `import { siXxx } from 'simple-icons'` y
 *      agregalo al array correspondiente con `path: siXxx.path`.
 *   2. Si es custom: agregá el SVG path a CUSTOM_PATHS y usalo abajo.
 */

import {
  // Developer platforms
  siGithub, siGitlab, siBitbucket, siDevdotto, siHashnode, siMedium,
  siStackoverflow, siCodesandbox, siNpm,
  // Social
  siX, siInstagram, siFacebook, siYoutube, siTiktok, siThreads,
  siBluesky, siMastodon, siReddit, siDiscord, siTwitch, siWhatsapp,
  // Creative
  siDribbble, siBehance, siFigma, siNotion, siSubstack,
  // Languages
  siTypescript, siJavascript, siPython, siRust, siGo, siPhp, siRuby,
  siKotlin, siSwift, siDart, siElixir, siCplusplus, siLua, siR, siOpenjdk,
  siHtml5, siCss,
  // Frontend frameworks
  siReact, siNextdotjs, siVuedotjs, siAngular, siSvelte, siSolid,
  siAstro, siRemix, siNuxt, siEmberdotjs,
  // Backend frameworks
  siNodedotjs, siDeno, siBun, siExpress, siNestjs, siDjango, siFastapi,
  siSpring, siLaravel, siRubyonrails,
  // Databases
  siPostgresql, siMysql, siMongodb, siRedis, siSqlite, siElasticsearch,
  siApachecassandra, siPrisma, siSupabase, siFirebase,
  // Cloud / DevOps
  siDocker, siKubernetes, siTerraform, siGooglecloud, siVercel,
  siNetlify, siDigitalocean, siCloudflare, siGithubactions, siAnsible,
  // Tools
  siGit, siTailwindcss, siSass, siWebpack, siVite, siJira,
  // Testing
  siJest, siCypress, siVitest, siSelenium,
  // Automation / workflow
  siN8n,
  // AI / ML — frameworks
  siTensorflow, siPytorch, siHuggingface, siScikitlearn,
  // AI — LLM providers & tools (simple-icons DOES ship these)
  siClaude, siAnthropic, siGooglegemini, siPerplexity, siMistralai,
  siOllama, siReplicate, siLangchain, siMeta,
  // AI — dev-assist + notebooks
  siGithubcopilot, siCursor, siJupyter, siGooglecolab, siKaggle,
  siPandas, siNumpy,
  // .NET
  siDotnet,
} from 'simple-icons';

export type IconCategory =
  | 'developer'
  | 'social'
  | 'creative'
  | 'contact'
  | 'language'
  | 'framework'
  | 'database'
  | 'devops'
  | 'tool'
  | 'ai';

export interface PortfolioIcon {
  /** ID estable persistido en el JSON del portafolio. */
  id: string;
  /** Display name — se muestra en el editor y como aria-label. */
  name: string;
  category: IconCategory;
  /** SVG path (24x24 viewBox, single path). */
  path: string;
  /** Placeholder de URL para el editor (opcional). */
  hint?: string;
}

// ═══════════════════════════════════════════════════════════════════════
// Custom SVG paths — brands removidas de simple-icons por trademark,
// y iconos genéricos (email/website/phone/rss). Todos 24x24 viewBox.
// ═══════════════════════════════════════════════════════════════════════

const CUSTOM_PATHS = {
  linkedin:
    'M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.86 3.37-1.86 3.6 0 4.27 2.37 4.27 5.45v6.3ZM5.34 7.44a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.78C.8 0 0 .78 0 1.75v20.5C0 23.22.8 24 1.78 24h20.44c.98 0 1.78-.78 1.78-1.75V1.75C24 .78 23.2 0 22.22 0Z',
  email:
    'M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 4v10h16V8l-8 5-8-5zm16-2H4l8 5 8-5z',
  website:
    'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  phone:
    'M20.01 15.38c-1.23 0-2.42-.2-3.53-.56a.977.977 0 0 0-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z',
  rss:
    'M6.18 15.64a2.18 2.18 0 0 1 2.18 2.18C8.36 19 7.38 20 6.18 20A2.18 2.18 0 0 1 4 17.82a2.18 2.18 0 0 1 2.18-2.18M4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27V4.44m0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93V10.1z',
  cv:
    'M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z',
  cal:
    'M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm0 16H5V8h14v11zM7 10h5v5H7v-5z',
  // OpenAI — rosette / hexagram oficial. Uso nominativo (identificación
  // de tecnologías usadas), no de endorsement.
  openai:
    'M22.282 9.821a5.985 5.985 0 0 0-.515-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5Z',
  // MCP (Model Context Protocol) — no tiene logo oficial. Uso un plug
  // + hub abstracto: dos "brazos" que se conectan a un nodo central,
  // sugieriendo protocolo/orquestación.
  mcp:
    'M12 2C10.34 2 9 3.34 9 5v3H6C4.9 8 4 8.9 4 10v4c0 3.31 2.69 6 6 6h4c3.31 0 6-2.69 6-6v-4c0-1.1-.9-2-2-2h-3V5c0-1.66-1.34-3-3-3zm-1 3c0-.55.45-1 1-1s1 .45 1 1v3h-2V5zm-5 5h12v4c0 2.21-1.79 4-4 4h-4c-2.21 0-4-1.79-4-4v-4zm3 2v2h2v-2H9zm4 0v2h2v-2h-2z',
  // Skills (Claude Skills) — dos sparkles/estrellas superpuestas.
  // Metáfora estándar de "AI-enhanced capability" en la industria.
  skills:
    'M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5L12 2zm7 12l1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3zM6 15l.75 2.25L9 18l-2.25.75L6 21l-.75-2.25L3 18l2.25-.75L6 15z',

  // ═══ AWS y servicios ═══
  // Removidos de simple-icons por trademark de Amazon. Uso nominativo
  // (identificación de tecnologías usadas), no de endorsement. Shapes
  // geométricos simples que sugieren cada servicio sin copiar los
  // logos oficiales de AWS pixel-por-pixel.

  // AWS — cubo isométrico + "smile" curve arriba. Metáfora del logo.
  aws:
    'M4 8l8-4 8 4v8l-8 4-8-4V8zm2 1.15v6.35l6 3v-6.35l-6-3zm12 0l-6 3v6.35l6-3V9.15zm-6-3.15l-5.5 2.75L12 11.5l5.5-2.75L12 5zm-6 14c1 1 3 2 6 2s5-1 6-2c-.5.5-2.5 1-6 1s-5.5-.5-6-1z',

  // S3 — bucket con la banda característica del logo.
  s3:
    'M5 6h14l-1.5 14a1 1 0 01-1 1H7.5a1 1 0 01-1-1L5 6zm2 2l.3 3h9.4L17 8H7zm.4 5l.3 3h8.6l.3-3H7.4zm.5 5l.2 2h7.8l.2-2H7.9z',

  // EC2 — server rack (chip-like) con esquinas cortadas.
  ec2:
    'M6 4h12v2h2v2h-2v2h2v2h-2v2h2v2h-2v2h-2v2h-2v-2h-2v2h-2v-2H8v2H6v-2H4v-2h2v-2H4v-2h2v-2H4V8h2V6H4V4h2zm2 4v8h8V8H8zm2 2h4v4h-4v-4z',

  // Lambda — el simbolo griego λ inscripto en un cuadrado redondeado.
  'aws-lambda':
    'M4 4h4l7 16h-4l-1.5-3.5-3-.5L4 20V4zm2 12l3-8 3.5 8h-6.5z',

  // RDS — cilindro clasico de database.
  'aws-rds':
    'M4 6c0-1.66 3.58-3 8-3s8 1.34 8 3v12c0 1.66-3.58 3-8 3s-8-1.34-8-3V6zm2 0c0 .55 2.24 1 6 1s6-.45 6-1-2.24-1-6-1-6 .45-6 1zm0 3c1.5.6 3.6 1 6 1s4.5-.4 6-1v3c-1.5.6-3.6 1-6 1s-4.5-.4-6-1V9zm0 6c1.5.6 3.6 1 6 1s4.5-.4 6-1v3c0 .55-2.24 1-6 1s-6-.45-6-1v-3z',

  // DynamoDB — dos cilindros superpuestos (D + D shape).
  'aws-dynamodb':
    'M3 4c0-1.1 2.5-2 6-2s6 .9 6 2v3c0 1.1-2.5 2-6 2s-6-.9-6-2V4zm10 5.9c2.5-.4 4-1.1 4-1.9V6c1.5.2 3 .8 3 2v3c0 1.1-2.5 2-6 2h-1v-3.1zM3 8c0 1.1 2.5 2 6 2s6-.9 6-2v4c0 1.1-2.5 2-6 2s-6-.9-6-2V8zm11 5.9c2-.2 4-.8 4-1.9V11c1.5.2 3 .8 3 2v3c0 1.1-2.5 2-6 2h-1v-2.1zM3 13c0 1.1 2.5 2 6 2s6-.9 6-2v4c0 1.1-2.5 2-6 2s-6-.9-6-2v-4zm11 5.9c2-.2 4-.8 4-1.9v-1c1.5.2 3 .8 3 2v3c0 1.1-2.5 2-6 2h-1v-2.1z',

  // CloudFront — globo con lineas radiales sugerendo CDN edges.
  'aws-cloudfront':
    'M12 2a10 10 0 100 20 10 10 0 000-20zm-1 2.07v3.93H7.7A8.02 8.02 0 0111 4.07zM6.06 10H10v4H6.06a8 8 0 010-4zM7.7 16H11v3.93A8.02 8.02 0 017.7 16zM13 19.93V16h3.3a8.02 8.02 0 01-3.3 3.93zM17.94 14H14v-4h3.94a8 8 0 010 4zM16.3 8H13V4.07A8.02 8.02 0 0116.3 8z',

  // API Gateway — hexagono con nodos en los vertices (representa
  // enrutamiento).
  'aws-api-gateway':
    'M12 2l9 5v10l-9 5-9-5V7l9-5zm0 2.3L5 8v8l7 4 7-4V8l-7-3.7zM9 9h6v2H9V9zm0 4h6v2H9v-2z',

  // IAM — escudo con silueta de persona (identity + access).
  'aws-iam':
    'M12 1L3 5v6c0 5 4 9 9 11 5-2 9-6 9-11V5l-9-4zm0 6a2.5 2.5 0 110 5 2.5 2.5 0 010-5zm0 6c2 0 5 1 5 3v1H7v-1c0-2 3-3 5-3z',

  // ECS — tres containers apilados con cintas ilustrando orquestacion.
  'aws-ecs':
    'M3 4h18v6H3V4zm2 2v2h4V6H5zm6 0v2h4V6h-4zm6 0v2h2V6h-2zM3 11h18v6H3v-6zm2 2v2h4v-2H5zm6 0v2h4v-2h-4zm6 0v2h2v-2h-2zM3 18h18v3H3v-3zm2 1v1h4v-1H5zm6 0v1h4v-1h-4zm6 0v1h2v-1h-2z',

  // SQS — cola de mensajes (rectangulos alineados horizontalmente
  // con flecha).
  'aws-sqs':
    'M2 8h4v8H2V8zm5 0h4v8H7V8zm5 0h4v8h-4V8zm5 3h3l-2-2h2l3 3-3 3h-2l2-2h-3v-2z',

  // CloudWatch — un ojo/reloj de monitoring dentro de una nube.
  'aws-cloudwatch':
    'M18 10c-.5-2-2-4-4-4s-4 2-4 4c-2 0-4 2-4 4s2 4 4 4h8c2 0 4-2 4-4s-2-4-4-4zm-6 3a2 2 0 100 4 2 2 0 000-4z',
};

// ═══════════════════════════════════════════════════════════════════════
// SOCIAL_ICONS — mostrados en el dropdown del editor de redes sociales
// ═══════════════════════════════════════════════════════════════════════

export const SOCIAL_ICONS: readonly PortfolioIcon[] = [
  // ── Developer platforms ──
  { id: 'github', name: 'GitHub', category: 'developer', path: siGithub.path, hint: 'https://github.com/tu-usuario' },
  { id: 'gitlab', name: 'GitLab', category: 'developer', path: siGitlab.path, hint: 'https://gitlab.com/tu-usuario' },
  { id: 'bitbucket', name: 'Bitbucket', category: 'developer', path: siBitbucket.path, hint: 'https://bitbucket.org/tu-usuario' },
  { id: 'devto', name: 'DEV.to', category: 'developer', path: siDevdotto.path, hint: 'https://dev.to/tu-usuario' },
  { id: 'hashnode', name: 'Hashnode', category: 'developer', path: siHashnode.path, hint: 'https://hashnode.com/@tu-usuario' },
  { id: 'medium', name: 'Medium', category: 'developer', path: siMedium.path, hint: 'https://medium.com/@tu-usuario' },
  { id: 'stackoverflow', name: 'Stack Overflow', category: 'developer', path: siStackoverflow.path, hint: 'https://stackoverflow.com/users/…' },
  { id: 'codesandbox', name: 'CodeSandbox', category: 'developer', path: siCodesandbox.path, hint: 'https://codesandbox.io/u/tu-usuario' },
  { id: 'npm', name: 'npm', category: 'developer', path: siNpm.path, hint: 'https://www.npmjs.com/~tu-usuario' },

  // ── Social (mainstream) ──
  { id: 'linkedin', name: 'LinkedIn', category: 'social', path: CUSTOM_PATHS.linkedin, hint: 'https://linkedin.com/in/tu-usuario' },
  { id: 'x', name: 'X (Twitter)', category: 'social', path: siX.path, hint: 'https://x.com/tu-usuario' },
  { id: 'instagram', name: 'Instagram', category: 'social', path: siInstagram.path, hint: 'https://instagram.com/tu-usuario' },
  { id: 'facebook', name: 'Facebook', category: 'social', path: siFacebook.path, hint: 'https://facebook.com/tu-usuario' },
  { id: 'youtube', name: 'YouTube', category: 'social', path: siYoutube.path, hint: 'https://youtube.com/@tu-canal' },
  { id: 'tiktok', name: 'TikTok', category: 'social', path: siTiktok.path, hint: 'https://tiktok.com/@tu-usuario' },
  { id: 'threads', name: 'Threads', category: 'social', path: siThreads.path, hint: 'https://threads.net/@tu-usuario' },
  { id: 'bluesky', name: 'Bluesky', category: 'social', path: siBluesky.path, hint: 'https://bsky.app/profile/tu-handle' },
  { id: 'mastodon', name: 'Mastodon', category: 'social', path: siMastodon.path, hint: 'https://mastodon.social/@tu-usuario' },
  { id: 'reddit', name: 'Reddit', category: 'social', path: siReddit.path, hint: 'https://reddit.com/user/tu-usuario' },
  { id: 'discord', name: 'Discord', category: 'social', path: siDiscord.path, hint: 'https://discord.gg/tu-invite' },
  { id: 'twitch', name: 'Twitch', category: 'social', path: siTwitch.path, hint: 'https://twitch.tv/tu-canal' },
  // WhatsApp — acepta URL con numero o con nickname nuevo de Meta.
  // El input del editor es texto libre, asi que cualquier variante valida.
  { id: 'whatsapp', name: 'WhatsApp', category: 'social', path: siWhatsapp.path, hint: 'https://wa.me/1234567890 o /@tu-usuario' },

  // ── Creative / Publishing ──
  { id: 'dribbble', name: 'Dribbble', category: 'creative', path: siDribbble.path, hint: 'https://dribbble.com/tu-usuario' },
  { id: 'behance', name: 'Behance', category: 'creative', path: siBehance.path, hint: 'https://behance.net/tu-usuario' },
  { id: 'figma', name: 'Figma', category: 'creative', path: siFigma.path, hint: 'https://figma.com/@tu-usuario' },
  { id: 'notion', name: 'Notion', category: 'creative', path: siNotion.path, hint: 'https://notion.so/tu-pagina' },
  { id: 'substack', name: 'Substack', category: 'creative', path: siSubstack.path, hint: 'https://tu-blog.substack.com' },

  // ── Contact / Generic ──
  { id: 'email', name: 'Email', category: 'contact', path: CUSTOM_PATHS.email, hint: 'mailto:tu@correo.com' },
  { id: 'website', name: 'Sitio web', category: 'contact', path: CUSTOM_PATHS.website, hint: 'https://tusitio.com' },
  { id: 'phone', name: 'Teléfono', category: 'contact', path: CUSTOM_PATHS.phone, hint: 'tel:+1234567890' },
  { id: 'rss', name: 'RSS', category: 'contact', path: CUSTOM_PATHS.rss, hint: 'https://tusitio.com/feed' },
  { id: 'cv', name: 'CV / Resume', category: 'contact', path: CUSTOM_PATHS.cv, hint: 'https://tusitio.com/cv.pdf' },
  { id: 'cal', name: 'Agendar reunión', category: 'contact', path: CUSTOM_PATHS.cal, hint: 'https://cal.com/tu-usuario' },
];

// ═══════════════════════════════════════════════════════════════════════
// TECH_ICONS — mostrados en el autocomplete del editor de stack técnico
// ═══════════════════════════════════════════════════════════════════════

export const TECH_ICONS: readonly PortfolioIcon[] = [
  // ── Languages ──
  { id: 'typescript', name: 'TypeScript', category: 'language', path: siTypescript.path },
  { id: 'javascript', name: 'JavaScript', category: 'language', path: siJavascript.path },
  { id: 'python', name: 'Python', category: 'language', path: siPython.path },
  { id: 'rust', name: 'Rust', category: 'language', path: siRust.path },
  { id: 'go', name: 'Go', category: 'language', path: siGo.path },
  { id: 'java', name: 'Java (OpenJDK)', category: 'language', path: siOpenjdk.path },
  { id: 'php', name: 'PHP', category: 'language', path: siPhp.path },
  { id: 'ruby', name: 'Ruby', category: 'language', path: siRuby.path },
  { id: 'kotlin', name: 'Kotlin', category: 'language', path: siKotlin.path },
  { id: 'swift', name: 'Swift', category: 'language', path: siSwift.path },
  { id: 'dart', name: 'Dart', category: 'language', path: siDart.path },
  { id: 'elixir', name: 'Elixir', category: 'language', path: siElixir.path },
  { id: 'cpp', name: 'C++', category: 'language', path: siCplusplus.path },
  { id: 'lua', name: 'Lua', category: 'language', path: siLua.path },
  { id: 'r', name: 'R', category: 'language', path: siR.path },
  { id: 'dotnet', name: '.NET / C#', category: 'language', path: siDotnet.path },
  // Web basics — con variantes de alias comunes (html5/css3 caen al
  // mismo icon que html/css para tolerar como el user escriba el stack).
  { id: 'html', name: 'HTML', category: 'language', path: siHtml5.path },
  { id: 'html5', name: 'HTML5', category: 'language', path: siHtml5.path },
  { id: 'css', name: 'CSS', category: 'language', path: siCss.path },
  { id: 'css3', name: 'CSS3', category: 'language', path: siCss.path },
  { id: 'js', name: 'JS', category: 'language', path: siJavascript.path },

  // ── Frontend frameworks ──
  { id: 'react', name: 'React', category: 'framework', path: siReact.path },
  { id: 'nextjs', name: 'Next.js', category: 'framework', path: siNextdotjs.path },
  { id: 'vue', name: 'Vue.js', category: 'framework', path: siVuedotjs.path },
  { id: 'angular', name: 'Angular', category: 'framework', path: siAngular.path },
  { id: 'svelte', name: 'Svelte', category: 'framework', path: siSvelte.path },
  { id: 'solid', name: 'Solid', category: 'framework', path: siSolid.path },
  { id: 'astro', name: 'Astro', category: 'framework', path: siAstro.path },
  { id: 'remix', name: 'Remix', category: 'framework', path: siRemix.path },
  { id: 'nuxt', name: 'Nuxt', category: 'framework', path: siNuxt.path },
  { id: 'ember', name: 'Ember.js', category: 'framework', path: siEmberdotjs.path },

  // ── Backend frameworks / runtimes ──
  { id: 'nodejs', name: 'Node.js', category: 'framework', path: siNodedotjs.path },
  { id: 'deno', name: 'Deno', category: 'framework', path: siDeno.path },
  { id: 'bun', name: 'Bun', category: 'framework', path: siBun.path },
  { id: 'express', name: 'Express', category: 'framework', path: siExpress.path },
  { id: 'nestjs', name: 'NestJS', category: 'framework', path: siNestjs.path },
  { id: 'django', name: 'Django', category: 'framework', path: siDjango.path },
  { id: 'fastapi', name: 'FastAPI', category: 'framework', path: siFastapi.path },
  { id: 'spring', name: 'Spring', category: 'framework', path: siSpring.path },
  { id: 'laravel', name: 'Laravel', category: 'framework', path: siLaravel.path },
  { id: 'rails', name: 'Ruby on Rails', category: 'framework', path: siRubyonrails.path },

  // ── Databases ──
  { id: 'postgresql', name: 'PostgreSQL', category: 'database', path: siPostgresql.path },
  { id: 'mysql', name: 'MySQL', category: 'database', path: siMysql.path },
  { id: 'mongodb', name: 'MongoDB', category: 'database', path: siMongodb.path },
  { id: 'redis', name: 'Redis', category: 'database', path: siRedis.path },
  { id: 'sqlite', name: 'SQLite', category: 'database', path: siSqlite.path },
  { id: 'elasticsearch', name: 'Elasticsearch', category: 'database', path: siElasticsearch.path },
  { id: 'cassandra', name: 'Cassandra', category: 'database', path: siApachecassandra.path },
  { id: 'prisma', name: 'Prisma', category: 'database', path: siPrisma.path },
  { id: 'supabase', name: 'Supabase', category: 'database', path: siSupabase.path },
  { id: 'firebase', name: 'Firebase', category: 'database', path: siFirebase.path },

  // ── Cloud / DevOps ──
  { id: 'docker', name: 'Docker', category: 'devops', path: siDocker.path },
  { id: 'kubernetes', name: 'Kubernetes', category: 'devops', path: siKubernetes.path },
  { id: 'terraform', name: 'Terraform', category: 'devops', path: siTerraform.path },
  { id: 'gcp', name: 'Google Cloud', category: 'devops', path: siGooglecloud.path },
  { id: 'vercel', name: 'Vercel', category: 'devops', path: siVercel.path },
  { id: 'netlify', name: 'Netlify', category: 'devops', path: siNetlify.path },
  { id: 'digitalocean', name: 'DigitalOcean', category: 'devops', path: siDigitalocean.path },
  { id: 'cloudflare', name: 'Cloudflare', category: 'devops', path: siCloudflare.path },
  { id: 'github-actions', name: 'GitHub Actions', category: 'devops', path: siGithubactions.path },
  { id: 'ansible', name: 'Ansible', category: 'devops', path: siAnsible.path },
  { id: 'n8n', name: 'n8n', category: 'devops', path: siN8n.path },

  // ── AWS y servicios ──
  // Removidos de simple-icons por trademark. Custom paths inline en
  // CUSTOM_PATHS. Los IDs "aws-*" son consistentes para autocomplete
  // (buscando "aws" salen todos juntos).
  { id: 'aws', name: 'AWS', category: 'devops', path: CUSTOM_PATHS.aws },
  { id: 's3', name: 'AWS S3', category: 'devops', path: CUSTOM_PATHS.s3 },
  { id: 'ec2', name: 'AWS EC2', category: 'devops', path: CUSTOM_PATHS.ec2 },
  { id: 'aws-lambda', name: 'AWS Lambda', category: 'devops', path: CUSTOM_PATHS['aws-lambda'] },
  { id: 'aws-rds', name: 'AWS RDS', category: 'devops', path: CUSTOM_PATHS['aws-rds'] },
  { id: 'aws-dynamodb', name: 'AWS DynamoDB', category: 'devops', path: CUSTOM_PATHS['aws-dynamodb'] },
  { id: 'aws-cloudfront', name: 'AWS CloudFront', category: 'devops', path: CUSTOM_PATHS['aws-cloudfront'] },
  { id: 'aws-api-gateway', name: 'AWS API Gateway', category: 'devops', path: CUSTOM_PATHS['aws-api-gateway'] },
  { id: 'aws-iam', name: 'AWS IAM', category: 'devops', path: CUSTOM_PATHS['aws-iam'] },
  { id: 'aws-ecs', name: 'AWS ECS', category: 'devops', path: CUSTOM_PATHS['aws-ecs'] },
  { id: 'aws-sqs', name: 'AWS SQS', category: 'devops', path: CUSTOM_PATHS['aws-sqs'] },
  { id: 'aws-cloudwatch', name: 'AWS CloudWatch', category: 'devops', path: CUSTOM_PATHS['aws-cloudwatch'] },

  // ── Tools ──
  { id: 'git', name: 'Git', category: 'tool', path: siGit.path },
  { id: 'tailwindcss', name: 'Tailwind CSS', category: 'tool', path: siTailwindcss.path },
  { id: 'sass', name: 'Sass', category: 'tool', path: siSass.path },
  { id: 'webpack', name: 'Webpack', category: 'tool', path: siWebpack.path },
  { id: 'vite', name: 'Vite', category: 'tool', path: siVite.path },
  { id: 'jira', name: 'Jira', category: 'tool', path: siJira.path },

  // ── Testing ──
  { id: 'jest', name: 'Jest', category: 'tool', path: siJest.path },
  { id: 'cypress', name: 'Cypress', category: 'tool', path: siCypress.path },
  { id: 'vitest', name: 'Vitest', category: 'tool', path: siVitest.path },
  { id: 'selenium', name: 'Selenium', category: 'tool', path: siSelenium.path },

  // ── AI / ML — frameworks ──
  { id: 'tensorflow', name: 'TensorFlow', category: 'ai', path: siTensorflow.path },
  { id: 'pytorch', name: 'PyTorch', category: 'ai', path: siPytorch.path },
  { id: 'huggingface', name: 'Hugging Face', category: 'ai', path: siHuggingface.path },
  { id: 'sklearn', name: 'scikit-learn', category: 'ai', path: siScikitlearn.path },
  { id: 'pandas', name: 'pandas', category: 'ai', path: siPandas.path },
  { id: 'numpy', name: 'NumPy', category: 'ai', path: siNumpy.path },

  // ── AI — LLM providers / models ──
  { id: 'openai', name: 'OpenAI', category: 'ai', path: CUSTOM_PATHS.openai },
  { id: 'claude', name: 'Claude', category: 'ai', path: siClaude.path },
  { id: 'anthropic', name: 'Anthropic', category: 'ai', path: siAnthropic.path },
  { id: 'gemini', name: 'Gemini', category: 'ai', path: siGooglegemini.path },
  { id: 'perplexity', name: 'Perplexity', category: 'ai', path: siPerplexity.path },
  { id: 'mistral', name: 'Mistral AI', category: 'ai', path: siMistralai.path },
  { id: 'meta-ai', name: 'Meta AI (LLaMA)', category: 'ai', path: siMeta.path },
  { id: 'ollama', name: 'Ollama', category: 'ai', path: siOllama.path },
  { id: 'replicate', name: 'Replicate', category: 'ai', path: siReplicate.path },

  // ── AI — orquestación / protocolos ──
  { id: 'langchain', name: 'LangChain', category: 'ai', path: siLangchain.path },
  { id: 'mcp', name: 'MCP (Model Context Protocol)', category: 'ai', path: CUSTOM_PATHS.mcp },
  { id: 'skills', name: 'Claude Skills', category: 'ai', path: CUSTOM_PATHS.skills },

  // ── AI — dev-assist + notebooks ──
  { id: 'copilot', name: 'GitHub Copilot', category: 'ai', path: siGithubcopilot.path },
  { id: 'cursor', name: 'Cursor', category: 'ai', path: siCursor.path },
  { id: 'jupyter', name: 'Jupyter', category: 'ai', path: siJupyter.path },
  { id: 'colab', name: 'Google Colab', category: 'ai', path: siGooglecolab.path },
  { id: 'kaggle', name: 'Kaggle', category: 'ai', path: siKaggle.path },
];

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

/** Todos los iconos (socials + tech) indexados en un array plano —
 *  útil para lookup por id sin importar de qué picker vino. */
export const ALL_ICONS: readonly PortfolioIcon[] = [...SOCIAL_ICONS, ...TECH_ICONS];

const _iconIndex = new Map<string, PortfolioIcon>(ALL_ICONS.map((i) => [i.id, i]));

export function findIconById(id: string): PortfolioIcon | undefined {
  return _iconIndex.get(id);
}

/** Filtra iconos por texto — usado por el autocomplete de tech. */
export function searchTechIcons(query: string): PortfolioIcon[] {
  const q = query.trim().toLowerCase();
  if (!q) return TECH_ICONS.slice(0, 12);
  return TECH_ICONS.filter(
    (i) => i.id.includes(q) || i.name.toLowerCase().includes(q),
  ).slice(0, 12);
}
