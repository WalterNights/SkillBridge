import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    callback: () => void;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toasts$ = new BehaviorSubject<Toast[]>([]);
  private defaultDuration = 5000;

  getToasts(): Observable<Toast[]> {
    return this.toasts$.asObservable();
  }

  success(message: string, title?: string, duration?: number): void {
    this.show({ type: 'success', message, title, duration });
  }

  error(message: string, title?: string, duration?: number): void {
    this.show({ type: 'error', message, title, duration });
  }

  warning(message: string, title?: string, duration?: number): void {
    this.show({ type: 'warning', message, title, duration });
  }

  info(message: string, title?: string, duration?: number): void {
    this.show({ type: 'info', message, title, duration });
  }

  show(toast: Omit<Toast, 'id'>): void {
    const id = this.generateId();
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? this.defaultDuration
    };

    const currentToasts = this.toasts$.value;
    this.toasts$.next([...currentToasts, newToast]);

    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        this.remove(id);
      }, newToast.duration);
    }
  }

  remove(id: string): void {
    const currentToasts = this.toasts$.value;
    this.toasts$.next(currentToasts.filter(toast => toast.id !== id));
  }

  clear(): void {
    this.toasts$.next([]);
  }

  private generateId(): string {
    return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }
}
