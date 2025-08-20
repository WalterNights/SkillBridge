import { Injectable } from "@angular/core";

type StorageType = 'session' | 'local';

@Injectable({ providedIn: 'root' })
export class StorageMethodComponent {

  setStorageItem(storageType: StorageType, key: string, value: string): void {
    const storage = storageType === 'session' ? sessionStorage : localStorage;
    return storage.setItem(key, value);
  }

  getStorageItem(storageType: StorageType, key: string): string | null {
    const storage = storageType === 'session' ? sessionStorage : localStorage;
    return storage.getItem(key);
  }
}