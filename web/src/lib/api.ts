/**
 * API configuration and utilities for backend communication
 */

/**
 * API Base URL - uses environment variable or defaults to localhost
 * Set NEXT_PUBLIC_API_URL environment variable to override
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * API fetcher function for SWR and general API calls
 * Automatically prepends API_BASE_URL for routes starting with /api
 *
 * @param url - The API endpoint URL (e.g., "/api/ideas" or full URL)
 * @returns Promise resolving to the JSON response
 */
export const fetcher = (url: string): Promise<any> => {
  const fullUrl = url.startsWith("/api") ? `${API_BASE_URL}${url}` : url;
  return fetch(fullUrl).then((res) => res.json());
};
