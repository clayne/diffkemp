//===----- DifferentialGlobalNumberState.h - Numbering global symbols -----===//
//
//       SimpLL - Program simplifier for analysis of semantic difference      //
//
// This file is published under Apache 2.0 license. See LICENSE for details.
// Author: Viktor Malik, vmalik@redhat.com
//===----------------------------------------------------------------------===//
///
/// \file
/// This file contains the declaration of the DifferentialGlobalNumberState
/// class that extends the GlobalNumberState class from the LLVM's function
/// comparator for the specific purposes of SimpLL.
///
//===----------------------------------------------------------------------===//

#ifndef DIFFKEMP_SIMPLL_DIFFERENTIALGLOBALNUMBERSTATE_H
#define DIFFKEMP_SIMPLL_DIFFERENTIALGLOBALNUMBERSTATE_H

#include <llvm/Transforms/Utils/FunctionComparator.h>

using namespace llvm;

/// Extension of GlobalNumberState.
/// Makes sure that matching globals in both compared modules get the same
/// number.
class DifferentialGlobalNumberState : public GlobalNumberState {
    // Mapping global values to numbers
    using ValueNumberMap = ValueMap<GlobalValue *, uint64_t>;
    ValueNumberMap GlobalNumbers;

    Module *First;
    Module *Second;

    u_int64_t nextNumber = 0;
  public:
    DifferentialGlobalNumberState(Module *first, Module *second) :
            First(first), Second(second) {}

    /// Get number of a global symbol. Corresponding symbols in compared modules
    /// get the same number.
    uint64_t getNumber(GlobalValue *value);

    /// Clear numbers mapping.
    void clear() {
        GlobalNumbers.clear();
    }
};

#endif //DIFFKEMP_SIMPLL_DIFFERENTIALGLOBALNUMBERSTATE_H