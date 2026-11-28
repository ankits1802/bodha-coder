import Image from "next/image";
import type { ReactNode } from "react";

interface SignaturePictureProps {
  src: string | null;
  alt: string;
  children?: ReactNode;
}

export function SignaturePicture({ src, alt, children }: SignaturePictureProps) {
  return (
    <div className="relative flex aspect-[5/2] w-full items-center justify-center overflow-hidden rounded-field border border-separator bg-paper">
      {src ? <Image src={src} alt={alt} fill unoptimized className="object-contain p-3" /> : children}
    </div>
  );
}
