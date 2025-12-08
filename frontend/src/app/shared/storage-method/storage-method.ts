import { Injectable } from "@angular/core";

type StorageType = 'session' | 'local';

/**
 * Service for managing browser storage (session and local storage)
 */
@Injectable({ providedIn: 'root' })
export class StorageMethodComponent {

  /**
   * Sets an item in the specified storage
   * @param storageType - Type of storage to use
   * @param key - Storage key
   * @param value - Value to store
   */
  setStorageItem(storageType: StorageType, key: string, value: string): void {
    const storage = storageType === 'session' ? sessionStorage : localStorage;
    storage.setItem(key, value);
  }

  /**
   * Gets an item from the specified storage
   * @param storageType - Type of storage to use
   * @param key - Storage key
   * @returns Stored value or null if not found
   */
  getStorageItem(storageType: StorageType, key: string): string | null {
    const storage = storageType === 'session' ? sessionStorage : localStorage;
    return storage.getItem(key);
  }
}