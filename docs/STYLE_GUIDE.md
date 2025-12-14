# Guía de Estilos - SkillBridge (SkilTak)

## Paleta de Colores del Proyecto

### Colores Principales

**Primary (Naranja Cálido)**
- `primary-50`: #FFF7ED
- `primary-100`: #FFEDD5
- `primary-200`: #FED7AA
- `primary-300`: #FDBA74
- `primary-400`: #FB923C
- `primary-500`: #F97316 ⭐ Principal
- `primary-600`: #EA580C
- `primary-700`: #C2410C
- `primary-800`: #9A3412
- `primary-900`: #7C2D12

**Secondary (Ámbar Dorado)**
- `secondary-400`: #FBBF24
- `secondary-500`: #F59E0B ⭐ Secundario
- `secondary-600`: #D97706

**Accent (Rosa Cálido)**
- `accent-500`: #F43F5E
- `accent-600`: #E11D48

### Modo Oscuro

**Backgrounds**
- `dark:bg-[#0A0A0B]` - Fondo principal
- `dark:bg-[#18181B]` - Fondo secundario (cards, navbars)
- `dark:bg-[#27272A]` - Fondo terciario (inputs, controles)

**Borders**
- `dark:border-[#27272A]` - Bordes principales
- `dark:border-[#3F3F46]` - Bordes secundarios

**Text**
- `dark:text-white` o `dark:text-[#FAFAFA]` - Texto principal
- `dark:text-gray-300` - Texto secundario
- `dark:text-gray-400` - Texto terciario/subtítulos

### Modo Claro

**Backgrounds**
- `bg-white` - Fondo principal
- `bg-gray-50` - Fondo de página
- `bg-gray-100` - Fondo de inputs/controles

**Borders**
- `border-gray-200` - Bordes principales
- `border-gray-300` - Bordes de inputs

**Text**
- `text-gray-900` - Texto principal
- `text-gray-700` - Texto secundario
- `text-gray-600` - Texto terciario
- `text-gray-500` - Placeholder/hints

## Componentes Estandarizados

### Botones

**Botón Principal**
```html
<button class="px-4 py-2 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium rounded-xl hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg hover:shadow-xl">
  Texto del botón
</button>
```

**Botón Secundario**
```html
<button class="px-4 py-2 bg-gray-100 dark:bg-[#27272A] hover:bg-gray-200 dark:hover:bg-[#3F3F46] text-gray-700 dark:text-gray-200 font-medium rounded-xl transition-colors">
  Texto del botón
</button>
```

### Inputs y Formularios

**Input de Texto**
```html
<input 
  type="text" 
  class="w-full px-4 py-2 bg-gray-50 dark:bg-[#27272A] border border-gray-300 dark:border-[#3F3F46] rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-white"
>
```

**Textarea**
```html
<textarea 
  class="w-full px-4 py-2 bg-gray-50 dark:bg-[#27272A] border border-gray-300 dark:border-[#3F3F46] rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-white"
></textarea>
```

### Cards

**Card Estándar**
```html
<div class="bg-white dark:bg-[#27272A] rounded-2xl border border-gray-200 dark:border-[#3F3F46] p-6 hover:shadow-xl transition-all">
  <!-- Contenido -->
</div>
```

### Headers y Navigation

**Header Principal**
- Fondo: `bg-white dark:bg-[#18181B]`
- Borde inferior: `border-b border-gray-200 dark:border-[#27272A]`
- Altura: `h-16`
- Backdrop blur: `backdrop-blur-md`

**Sidebar**
- Fondo: `bg-white dark:bg-[#18181B]`
- Borde derecho: `border-r border-gray-200 dark:border-[#27272A]`
- Ancho: `w-64`

### Links

**Link Principal**
```html
<a class="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
  Enlace
</a>
```

### Badges y Tags

**Badge de Estado**
```html
<span class="px-3 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 text-xs font-medium rounded-full">
  Activo
</span>
```

### Iconos y Avatares

**Avatar con Gradiente**
```html
<div class="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center text-white font-semibold shadow-md">
  {{ initials }}
</div>
```

## Reglas de Diseño

### Espaciado
- Usar `gap-3` o `gap-4` entre elementos relacionados
- Usar `gap-6` o `gap-8` entre secciones
- Padding de cards: `p-6` o `p-8`
- Margin entre secciones: `mb-8` o `mb-12`

### Bordes
- Radius estándar: `rounded-xl` (cards, botones)
- Radius grande: `rounded-2xl` (modales, contenedores principales)
- Radius completo: `rounded-full` (avatares, badges)

### Sombras
- Hover en cards: `hover:shadow-xl`
- Botones principales: `shadow-lg hover:shadow-xl`
- Modales: `shadow-2xl`

### Transiciones
- Estándar: `transition-colors` o `transition-all`
- Duración: `duration-200` o `duration-300`

## Prohibiciones

### ❌ No Usar
- `indigo-*` - Usar `primary-*` en su lugar
- `blue-*` - Usar `amber-*` o `primary-*` según contexto
- `purple-*` - Usar `accent-*` si es necesario
- Colores hardcoded - Siempre usar las clases de Tailwind del tema

### ❌ No Mezclar
- No mezclar `bg-white` con `dark:bg-gray-800` (usar `dark:bg-[#18181B]`)
- No usar valores hex directos sin definirlos en el tema
- No usar colores diferentes en componentes similares

## Ejemplos de Componentes Correctos

### Modal de Carga
```html
<div class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center">
  <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 w-80 text-center">
    <svg class="animate-spin h-10 w-10 text-primary-600 dark:text-primary-400">...</svg>
    <p class="mt-4 text-gray-700 dark:text-gray-300 font-semibold">Cargando...</p>
  </div>
</div>
```

### Dropdown Menu
```html
<div class="absolute right-0 mt-2 w-56 rounded-xl bg-white dark:bg-[#27272A] shadow-xl border border-gray-200 dark:border-[#3F3F46]">
  <div class="p-3 border-b border-gray-200 dark:border-[#3F3F46]">
    <p class="text-sm font-semibold text-gray-900 dark:text-white">Usuario</p>
  </div>
  <button class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#3F3F46]">
    Opción
  </button>
</div>
```

## Checklist de Consistencia

Antes de hacer commit, verifica:

- [ ] Todos los colores usan el esquema definido (primary, secondary, accent)
- [ ] Los fondos en dark mode usan `[#0A0A0B]`, `[#18181B]`, o `[#27272A]`
- [ ] Los bordes en dark mode usan `[#27272A]` o `[#3F3F46]`
- [ ] Los textos tienen variantes dark mode apropiadas
- [ ] Los botones principales usan el gradiente naranja
- [ ] Los inputs tienen focus ring con `primary-500`
- [ ] Las transiciones están implementadas
- [ ] Los border-radius son consistentes
- [ ] Las sombras son apropiadas para cada elemento

## Recursos

- **Tailwind Config**: `frontend/tailwind.config.js`
- **Estilos Globales**: `frontend/src/styles.scss`
- **Paleta de Referencia**: https://tailwindcss.com/docs/customizing-colors

---

**Última actualización**: Diciembre 2025
**Versión del Sistema de Diseño**: 2.0
