#ifndef KITE_BVP_SOLVER_INCLUDE_OBJ_H
#define KITE_BVP_SOLVER_INCLUDE_OBJ_H

#include <roboptim/core/io.hh>
#include <roboptim/core/solver.hh>
#include <roboptim/core/alloc.hh>

#include <roboptim/core/plugin/ipopt/ipopt.hh>
#include <roboptim/core/differentiable-function.hh>
#include <roboptim/core/solver-factory.hh>

namespace ro = roboptim;
namespace ca {
    namespace kite_bvp_solver {
        template<class T, size_t degree_>
        struct F : public ro::DifferentiableFunction {
            unsigned n;

            F() : ro::DifferentiableFunction(2 * degree_ + 3, 1, "obj") {
                n = 2 * degree_ + 3;
//                std::cout << "Initializing obj with num params " << n << std::endl;


            }

            void impl_compute(result_ref result, const_argument_ref x) const {

                result[0] = (x[n - 1] + x[n - 2] + x[n - 3]);
//                std::cout << result[0] << std::endl;

            }

            void impl_gradient(gradient_ref grad, const_argument_ref x, size_type) const {
                grad[n - 1] = 1;
                grad[n - 2] = 1;
                grad[n - 3] = 1;
                for (int i = 0; i <= n - 4; ++i) {
                    grad[i] = 0;
                }

            }

        };
    }
}
#endif
