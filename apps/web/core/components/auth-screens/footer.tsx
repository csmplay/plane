/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";

const BRAND_LOGOS: {
  id: string;
  src: string;
}[] = [
  {
    id: "csm",
    src: "https://cdn.csmpro.ru/brand/csm/logos/CSM_outline.svg",
  },
];

export function AuthFooter() {
  return (
    <div className="flex flex-col items-center gap-6">
      <div className="flex w-full flex-wrap items-center justify-center gap-x-10 gap-y-4">
        {BRAND_LOGOS.map((brand) => (
          <div key={brand.id} className="flex h-7 items-center justify-center">
            <img src={brand.src} alt={brand.id} className="h-7 w-auto object-contain" loading="lazy" />
          </div>
        ))}
      </div>
    </div>
  );
}
