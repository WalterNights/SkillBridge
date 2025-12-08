import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

// Fade In Animation
export const fadeIn = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(10px)' }),
    animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);

// Fade Out Animation
export const fadeOut = trigger('fadeOut', [
  transition(':leave', [
    animate('200ms ease-in', style({ opacity: 0, transform: 'translateY(-10px)' }))
  ])
]);

// Slide In From Left
export const slideInLeft = trigger('slideInLeft', [
  transition(':enter', [
    style({ transform: 'translateX(-100%)', opacity: 0 }),
    animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
  ])
]);

// Slide In From Right
export const slideInRight = trigger('slideInRight', [
  transition(':enter', [
    style({ transform: 'translateX(100%)', opacity: 0 }),
    animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
  ])
]);

// Scale In
export const scaleIn = trigger('scaleIn', [
  transition(':enter', [
    style({ transform: 'scale(0.9)', opacity: 0 }),
    animate('200ms ease-out', style({ transform: 'scale(1)', opacity: 1 }))
  ])
]);

// Scale Out
export const scaleOut = trigger('scaleOut', [
  transition(':leave', [
    animate('150ms ease-in', style({ transform: 'scale(0.9)', opacity: 0 }))
  ])
]);

// List Stagger Animation
export const listStagger = trigger('listStagger', [
  transition('* => *', [
    query(':enter', [
      style({ opacity: 0, transform: 'translateY(20px)' }),
      stagger(50, [
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ], { optional: true })
  ])
]);

// Expand/Collapse Animation
export const expandCollapse = trigger('expandCollapse', [
  transition(':enter', [
    style({ height: 0, opacity: 0, overflow: 'hidden' }),
    animate('300ms ease-out', style({ height: '*', opacity: 1 }))
  ]),
  transition(':leave', [
    style({ height: '*', opacity: 1, overflow: 'hidden' }),
    animate('200ms ease-in', style({ height: 0, opacity: 0 }))
  ])
]);

// Rotate Animation
export const rotate = trigger('rotate', [
  transition('* => *', [
    animate('200ms ease-in-out')
  ])
]);

// Shake Animation (for errors)
export const shake = trigger('shake', [
  transition('* => *', [
    animate('500ms', style({ transform: 'translateX(0)' })),
    animate('50ms', style({ transform: 'translateX(-5px)' })),
    animate('50ms', style({ transform: 'translateX(5px)' })),
    animate('50ms', style({ transform: 'translateX(-5px)' })),
    animate('50ms', style({ transform: 'translateX(5px)' })),
    animate('50ms', style({ transform: 'translateX(0)' }))
  ])
]);

// Modal/Dialog Animation
export const modalAnimation = trigger('modalAnimation', [
  transition(':enter', [
    style({ opacity: 0 }),
    animate('200ms ease-out', style({ opacity: 1 })),
    query('.modal-content', [
      style({ transform: 'scale(0.9)', opacity: 0 }),
      animate('300ms 100ms ease-out', style({ transform: 'scale(1)', opacity: 1 }))
    ], { optional: true })
  ]),
  transition(':leave', [
    query('.modal-content', [
      animate('200ms ease-in', style({ transform: 'scale(0.9)', opacity: 0 }))
    ], { optional: true }),
    animate('200ms ease-in', style({ opacity: 0 }))
  ])
]);

// Slide Up Animation
export const slideUp = trigger('slideUp', [
  transition(':enter', [
    style({ transform: 'translateY(100%)', opacity: 0 }),
    animate('400ms cubic-bezier(0.4, 0, 0.2, 1)', style({ transform: 'translateY(0)', opacity: 1 }))
  ]),
  transition(':leave', [
    animate('300ms cubic-bezier(0.4, 0, 1, 1)', style({ transform: 'translateY(100%)', opacity: 0 }))
  ])
]);

// Slide Down Animation
export const slideDown = trigger('slideDown', [
  transition(':enter', [
    style({ transform: 'translateY(-100%)', opacity: 0 }),
    animate('400ms cubic-bezier(0.4, 0, 0.2, 1)', style({ transform: 'translateY(0)', opacity: 1 }))
  ]),
  transition(':leave', [
    animate('300ms cubic-bezier(0.4, 0, 1, 1)', style({ transform: 'translateY(-100%)', opacity: 0 }))
  ])
]);

// Fade and Slide Animation (combined)
export const fadeSlide = trigger('fadeSlide', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(20px)' }),
    animate('400ms cubic-bezier(0.4, 0, 0.2, 1)', style({ opacity: 1, transform: 'translateY(0)' }))
  ]),
  transition(':leave', [
    animate('200ms cubic-bezier(0.4, 0, 1, 1)', style({ opacity: 0, transform: 'translateY(20px)' }))
  ])
]);

// Route Animation
export const routeAnimation = trigger('routeAnimation', [
  transition('* <=> *', [
    query(':enter, :leave', [
      style({
        position: 'absolute',
        width: '100%',
        opacity: 0
      })
    ], { optional: true }),
    query(':enter', [
      animate('300ms ease-out', style({ opacity: 1 }))
    ], { optional: true })
  ])
]);
