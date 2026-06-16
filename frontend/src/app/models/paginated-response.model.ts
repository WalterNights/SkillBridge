/**
 * Shape estándar de las respuestas paginadas de DRF
 * (`rest_framework.pagination.PageNumberPagination`).
 *
 * Los servicios desempaquetan `results` antes de devolver al componente,
 * para que la capa de UI no tenga que conocer la paginación.
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
