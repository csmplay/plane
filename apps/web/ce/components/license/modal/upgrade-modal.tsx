/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { EModalWidth, ModalCore } from "@plane/ui";
import { cn } from "@plane/utils";

// Constants
const COMMON_CARD_CLASSNAME = "flex flex-col w-full h-full justify-end col-span-12 sm:col-span-6 xl:col-span-3";

export type PaidPlanUpgradeModalProps = {
  isOpen: boolean;
  handleClose: () => void;
};

export const PaidPlanUpgradeModal = observer(function PaidPlanUpgradeModal(props: PaidPlanUpgradeModalProps) {
  const { isOpen, handleClose } = props;

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} width={EModalWidth.VIIXL} className="rounded-2xl">
      <div className="max-h-[90vh] overflow-auto p-10">
        <div className="grid h-full grid-cols-12 gap-6">
          {/* Free Plan Section */}
          <div className={cn(COMMON_CARD_CLASSNAME)}>
            <div className="flex text-24 leading-8 font-bold">CSM Plane</div>
          </div>
        </div>
      </div>
    </ModalCore>
  );
});
