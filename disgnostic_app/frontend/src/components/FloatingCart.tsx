import { useEffect, useState } from "react";
import { getCartCount, getCartTotal, subscribeToCartChanges } from "../cartStore";

interface FloatingCartProps {
  onClick: () => void;
}

const FloatingCart = ({ onClick }: FloatingCartProps) => {
  const [count, setCount] = useState(getCartCount);
  const [total, setTotal] = useState(getCartTotal);

  useEffect(() => {
    const updateCart = () => {
      setCount(getCartCount());
      setTotal(getCartTotal());
    };

    const unsubscribe = subscribeToCartChanges(updateCart);
    return unsubscribe;
  }, []);

  // Don't show when cart is empty
  if (count === 0) return null;

  const formatTotal = (value: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(value);

  return (
    <button
      type="button"
      className="floating-cart"
      onClick={onClick}
      aria-label={`Shopping cart with ${count} items, total ${formatTotal(total)}`}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="floating-cart-icon"
      >
        <circle cx="9" cy="21" r="1" />
        <circle cx="20" cy="21" r="1" />
        <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
      </svg>
      <span className="floating-cart-info">
        <span className="floating-cart-count">
          {count} {count === 1 ? "item" : "items"}
        </span>
        <span className="floating-cart-total">{formatTotal(total)}</span>
      </span>
    </button>
  );
};

export default FloatingCart;

