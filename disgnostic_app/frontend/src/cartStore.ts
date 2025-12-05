/**
 * Cart state management with localStorage persistence.
 * Provides a simple store for managing cart items across the application.
 */

export interface CartItem {
  partNumber: string;
  description: string;
  price: number;
  quantity: number;
  imageUrl?: string;
}

const CART_STORAGE_KEY = "techcheck_cart";

// Event for cart updates
const cartChangeEvent = new Event("cartChange");

/**
 * Get all items currently in the cart.
 */
export const getCartItems = (): CartItem[] => {
  try {
    const stored = localStorage.getItem(CART_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

/**
 * Save cart items to localStorage.
 */
const saveCart = (items: CartItem[]): void => {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(cartChangeEvent);
};

/**
 * Add an item to the cart. If it already exists, increment the quantity.
 */
export const addToCart = (item: Omit<CartItem, "quantity"> & { quantity?: number }): void => {
  const items = getCartItems();
  const existing = items.find((i) => i.partNumber === item.partNumber);

  if (existing) {
    existing.quantity += item.quantity ?? 1;
  } else {
    items.push({
      partNumber: item.partNumber,
      description: item.description,
      price: item.price,
      quantity: item.quantity ?? 1,
      imageUrl: item.imageUrl,
    });
  }

  saveCart(items);
};

/**
 * Remove an item from the cart by part number.
 */
export const removeFromCart = (partNumber: string): void => {
  const items = getCartItems().filter((i) => i.partNumber !== partNumber);
  saveCart(items);
};

/**
 * Update the quantity of an item in the cart.
 */
export const updateQuantity = (partNumber: string, quantity: number): void => {
  const items = getCartItems();
  const item = items.find((i) => i.partNumber === partNumber);

  if (item) {
    if (quantity <= 0) {
      removeFromCart(partNumber);
    } else {
      item.quantity = quantity;
      saveCart(items);
    }
  }
};

/**
 * Clear all items from the cart.
 */
export const clearCart = (): void => {
  localStorage.removeItem(CART_STORAGE_KEY);
  window.dispatchEvent(cartChangeEvent);
};

/**
 * Get the total number of items in the cart.
 */
export const getCartCount = (): number => {
  return getCartItems().reduce((sum, item) => sum + item.quantity, 0);
};

/**
 * Get the total price of all items in the cart.
 */
export const getCartTotal = (): number => {
  return getCartItems().reduce((sum, item) => sum + item.price * item.quantity, 0);
};

/**
 * Subscribe to cart changes.
 */
export const subscribeToCartChanges = (callback: () => void): (() => void) => {
  window.addEventListener("cartChange", callback);
  return () => window.removeEventListener("cartChange", callback);
};

