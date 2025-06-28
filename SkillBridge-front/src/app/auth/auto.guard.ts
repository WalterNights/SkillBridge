import { inject, Injectable } from "@angular/core";
import { CanActivateFn, Router } from "@angular/router";

export const AutoGuard: CanActivateFn = (route, state) => {
    const isAuthenticated = sessionStorage.getItem('access_token');
    if(!isAuthenticated) {
        const router = inject(Router);
        router.navigate(['/auth/login']);
        return false
    }
    return true;
};