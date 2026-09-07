/** Logo de marca de Reminia — el MISMO en toda la app (panel, tablet, web comercial).
 *  Azulejo salvia con anillos concéntricos (evocan la memoria, los recuerdos que
 *  vuelven) y un punto coral en el centro. */
import { colors, fonts } from "../theme";

export function Logo({
  size = 30,
  textSize = 26,
  showText = true,
}: {
  size?: number;
  textSize?: number;
  showText?: boolean;
}) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <svg width={size} height={size} viewBox="0 0 40 40" aria-label="Reminia" role="img">
        <rect width="40" height="40" rx="11" fill="#12A99B" />
        <circle cx="20" cy="20" r="12.5" fill="none" stroke="#FFFEFB" strokeWidth="2.6" />
        <circle cx="20" cy="20" r="7" fill="none" stroke="#FFFEFB" strokeWidth="2.6" />
        <circle cx="20" cy="20" r="2.4" fill="#F08A6B" />
      </svg>
      {showText && (
        <span style={{ fontFamily: fonts.serif, fontSize: textSize, fontWeight: 600, color: colors.ink }}>
          Reminia
        </span>
      )}
    </div>
  );
}
