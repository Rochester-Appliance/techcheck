import { useEffect, useState } from "react";
import {
  CartItem,
  getCartItems,
  getCartTotal,
  removeFromCart,
  updateQuantity,
  subscribeToCartChanges,
  clearCart,
} from "../cartStore";
import axios from "axios";

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const CartDrawer = ({ isOpen, onClose }: CartDrawerProps) => {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setItems(getCartItems());
    const unsubscribe = subscribeToCartChanges(() => {
      setItems(getCartItems());
    });
    return unsubscribe;
  }, []);

  const total = getCartTotal();

  const handleCheckout = async () => {
    if (items.length === 0) return;

    setIsLoading(true);
    setError(null);

    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    try {
      const response = await axios.post(`${API_BASE}/checkout/create-session`, {
        items: items.map((item) => ({
          part_number: item.partNumber,
          description: item.description,
          price: item.price,
          quantity: item.quantity,
          image_url: item.imageUrl || null,
        })),
        success_url: `${window.location.origin}?checkout=success`,
        cancel_url: `${window.location.origin}?checkout=cancelled`,
      });

      // Redirect to Stripe Checkout
      window.location.href = response.data.checkout_url;
    } catch (err) {
      console.error("Checkout error:", err);
      setError("Failed to start checkout. Please try again.");
      setIsLoading(false);
    }
  };

  const handleClearCart = () => {
    clearCart();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="cart-overlay" onClick={onClose} />
      <div className="cart-drawer">
        <div className="cart-header">
          <h3>Shopping Cart</h3>
          <button type="button" className="cart-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="cart-content">
          {items.length === 0 ? (
            <div className="cart-empty">
              <p>Your cart is empty</p>
              <p className="muted">Add parts from the diagnosis to get started.</p>
            </div>
          ) : (
            <ul className="cart-items">
              {items.map((item) => (
                <li key={item.partNumber} className="cart-item">
                  <div className="cart-item-info">
                    <strong>{item.partNumber}</strong>
                    <p className="cart-item-desc">{item.description}</p>
                    <p className="cart-item-price">${item.price.toFixed(2)}</p>
                  </div>
                  <div className="cart-item-actions">
                    <div className="quantity-controls">
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.partNumber, item.quantity - 1)}
                        disabled={item.quantity <= 1}
                      >
                        −
                      </button>
                      <span>{item.quantity}</span>
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.partNumber, item.quantity + 1)}
                      >
                        +
                      </button>
                    </div>
                    <button
                      type="button"
                      className="cart-remove-btn"
                      onClick={() => removeFromCart(item.partNumber)}
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {items.length > 0 && (
          <div className="cart-footer">
            <div className="cart-total">
              <span>Total:</span>
              <strong>${total.toFixed(2)}</strong>
            </div>

            {error && <p className="cart-error">{error}</p>}

            <button
              type="button"
              className="btn btn-primary cart-checkout-btn"
              onClick={handleCheckout}
              disabled={isLoading}
            >
              {isLoading ? "Processing..." : "Proceed to Checkout"}
            </button>

            <button
              type="button"
              className="btn btn-secondary cart-clear-btn"
              onClick={handleClearCart}
            >
              Clear Cart
            </button>
          </div>
        )}
      </div>
    </>
  );
};

export default CartDrawer;

