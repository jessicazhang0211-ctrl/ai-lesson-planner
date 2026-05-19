export default function Button({
  children,
  icon: Icon,
  variant = "default",
  type = "button",
  className = "",
  ...props
}) {
  return (
    <button type={type} className={`btn ${variant} ${className}`.trim()} {...props}>
      {Icon ? <Icon size={16} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
}
