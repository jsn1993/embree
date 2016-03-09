// ======================================================================== //
// Copyright 2009-2015 Intel Corporation                                    //
//                                                                          //
// Licensed under the Apache License, Version 2.0 (the "License");          //
// you may not use this file except in compliance with the License.         //
// You may obtain a copy of the License at                                  //
//                                                                          //
//     http://www.apache.org/licenses/LICENSE-2.0                           //
//                                                                          //
// Unless required by applicable law or agreed to in writing, software      //
// distributed under the License is distributed on an "AS IS" BASIS,        //
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. //
// See the License for the specific language governing permissions and      //
// limitations under the License.                                           //
// ======================================================================== //

#pragma once

#include "../../common/ray.h"

namespace embree
{
  namespace isa
  {
    struct Cylinder
    {
      const Vec3fa p0;  //!< start location
      const Vec3fa p1;  //!< end position
      const float rr;   //!< squared radius of cylinder

      __forceinline Cylinder(const Vec3fa& p0, const Vec3fa& p1, const float r) 
        : p0(p0), p1(p1), rr(sqr(r)) {}

      __forceinline Cylinder(const Vec3fa& p0, const Vec3fa& p1, const float rr, bool) 
        : p0(p0), p1(p1), rr(rr) {}

      __forceinline bool intersect(const Vec3fa& org,
                                   const Vec3fa& dir, 
                                   BBox1f& t_o, 
                                   float& u0_o, Vec3fa& Ng0_o,
                                   float& u1_o, Vec3fa& Ng1_o) const
      {
        /* calculate quadratic equation to solve */
        const Vec3fa v0 = p0-org;
        const Vec3fa v1 = p1-org;

        const float rl = rcp_length(v1-v0);
        const Vec3fa P0 = v0, dP = (v1-v0)*rl;
        const Vec3fa O = -P0, dO = dir;
        
        const float dOdO = dot(dO,dO);
        const float OdO = dot(dO,O);
        const float OO = dot(O,O);
        const float dOz = dot(dP,dO);
        const float Oz = dot(dP,O);
        
        const float A = dOdO - sqr(dOz);
        const float B = 2.0f * (OdO - dOz*Oz);
        const float C = OO - sqr(Oz) - rr;
        
        /* we miss the cylinder if determinant is smaller than zero */
        const float D = B*B - 4.0f*A*C;
        if (D < 0.0f) {
          t_o = BBox1f(pos_inf,neg_inf);
          return false;
        }
        
        /* special case for rays that are parallel to the cylinder */
        const float eps = 16.0f*float(ulp)*max(abs(dOdO),abs(sqr(dOz)));
        if (abs(A) < eps) 
        {
          if (C <= 0.0f) {
            t_o = BBox1f(neg_inf,pos_inf);
            return true;
          } else {
            t_o = BBox1f(pos_inf,neg_inf);
            return false;
          }
        }
        
        /* standard case for rays that are not parallel to the cylinder */
        const float Q = sqrt(D);
        const float rcp_2A = rcp(2.0f*A);
        const float t0 = (-B-Q)*rcp_2A;
        const float t1 = (-B+Q)*rcp_2A;
        
        /* calculates u and Ng for near hit */
        {
          u0_o = (Oz+t0*dOz)*rl;
          const Vec3fa Pr = t_o.lower*dir;
          const Vec3fa Pl = v0 + u0_o*(v1-v0);
          Ng0_o = Pr-Pl;
        }

        /* calculates u and Ng for far hit */
        {
          u1_o = (Oz+t1*dOz)*rl;
          const Vec3fa Pr = t_o.lower*dir;
          const Vec3fa Pl = v0 + u1_o*(v1-v0);
          Ng1_o = Pr-Pl;
        }

        t_o.lower = t0;
        t_o.upper = t1;
        return true;
      }

      __forceinline bool intersect(const Vec3fa& org_i, const Vec3fa& dir, BBox1f& t_o) const
      {
        float u0_o; Vec3fa Ng0_o;
        float u1_o; Vec3fa Ng1_o;
        return intersect(org_i,dir,t_o,u0_o,Ng0_o,u1_o,Ng1_o);
      }

      static bool verify(const size_t id, const Cylinder& cylinder, const Ray& ray, bool shouldhit, const float t0, const float t1)
      {
        float eps = 0.001f;
        BBox1f t; bool hit;
        hit = cylinder.intersect(ray.org,ray.dir,t);

        bool failed = hit != shouldhit;
        if (shouldhit) failed |= isinf(t0) ? t0 != t.lower : abs(t0-t.lower) > eps;
        if (shouldhit) failed |= isinf(t1) ? t1 != t.upper : abs(t1-t.upper) > eps;
        if (!failed) return true;
        std::cout << "Cylinder test " << id << " failed: cylinder = " << cylinder << ", ray = " << ray << ", hit = " << hit << ", t = " << t << std::endl; 
        return false;
      }

      /* verify cylinder class */
      static bool verify()
      {
        bool passed = true;
        const Cylinder cylinder(Vec3fa(0.0f,0.0f,0.0f),Vec3fa(1.0f,0.0f,0.0f),1.0f);
        passed &= verify(0,cylinder,Ray(Vec3fa(-2.0f,1.0f,0.0f),Vec3fa( 0.0f,-1.0f,+0.0f),0.0f,float(inf)),true,0.0f,2.0f);
        passed &= verify(1,cylinder,Ray(Vec3fa(+2.0f,1.0f,0.0f),Vec3fa( 0.0f,-1.0f,+0.0f),0.0f,float(inf)),true,0.0f,2.0f);
        passed &= verify(2,cylinder,Ray(Vec3fa(+2.0f,1.0f,2.0f),Vec3fa( 0.0f,-1.0f,+0.0f),0.0f,float(inf)),false,0.0f,0.0f);
        passed &= verify(3,cylinder,Ray(Vec3fa(+0.0f,0.0f,0.0f),Vec3fa( 1.0f, 0.0f,+0.0f),0.0f,float(inf)),true,neg_inf,pos_inf);
        passed &= verify(4,cylinder,Ray(Vec3fa(+0.0f,0.0f,0.0f),Vec3fa(-1.0f, 0.0f,+0.0f),0.0f,float(inf)),true,neg_inf,pos_inf);
        passed &= verify(5,cylinder,Ray(Vec3fa(+0.0f,2.0f,0.0f),Vec3fa( 1.0f, 0.0f,+0.0f),0.0f,float(inf)),false,pos_inf,neg_inf);
        passed &= verify(6,cylinder,Ray(Vec3fa(+0.0f,2.0f,0.0f),Vec3fa(-1.0f, 0.0f,+0.0f),0.0f,float(inf)),false,pos_inf,neg_inf);
        return passed;
      }

      /*! output operator */
      friend __forceinline std::ostream& operator<<(std::ostream& cout, const Cylinder& c) {
        return cout << "Cylinder { p0 = " << c.p0 << ", p1 = " << c.p1 << ", r = " << sqrtf(c.rr) << "}";
      }
    };

    template<int N>
      struct CylinderN
    {
      typedef Vec3<vfloat<N>> Vec3vfN;
      
      const Vec3vfN p0;     //!< start location
      const Vec3vfN p1;     //!< end position
      const vfloat<N> rr;   //!< squared radius of cylinder

      __forceinline CylinderN(const Vec3vfN& p0, const Vec3vfN& p1, const vfloat<N>& r) 
        : p0(p0), p1(p1), rr(sqr(r)) {}

      __forceinline CylinderN(const Vec3vfN& p0, const Vec3vfN& p1, const vfloat<N>& rr, bool) 
        : p0(p0), p1(p1), rr(rr) {}

     
      __forceinline vbool<N> intersect(const Vec3fa& org, const Vec3fa& dir, 
                                       BBox<vfloat<N>>& t_o, 
                                       vfloat<N>& u0_o, Vec3vfN& Ng0_o,
                                       vfloat<N>& u1_o, Vec3vfN& Ng1_o) const
      {
        /* calculate quadratic equation to solve */
        const Vec3vfN v0 = p0-Vec3vfN(org);
        const Vec3vfN v1 = p1-Vec3vfN(org);
        
        const vfloat<N> rl = rcp_length(v1-v0);
        const Vec3vfN P0 = v0, dP = (v1-v0)*rl;
        const Vec3vfN O = -P0, dO = dir;
        
        const vfloat<N> dOdO = dot(dO,dO);
        const vfloat<N> OdO = dot(dO,O);
        const vfloat<N> OO = dot(O,O);
        const vfloat<N> dOz = dot(dP,dO);
        const vfloat<N> Oz = dot(dP,O);
        
        const vfloat<N> A = dOdO - sqr(dOz);
        const vfloat<N> B = 2.0f * (OdO - dOz*Oz);
        const vfloat<N> C = OO - sqr(Oz) - rr;
        
        /* we miss the cylinder if determinant is smaller than zero */
        const vfloat<N> D = B*B - 4.0f*A*C;
        vbool<N> valid = D >= 0.0f;
        if (none(valid)) {
          t_o = BBox<vfloat<N>>(empty);
          return valid;
        }

        /* standard case for rays that are not parallel to the cylinder */
        const vfloat<N> Q = sqrt(D);
        const vfloat<N> rcp_2A = rcp(2.0f*A);
        const vfloat<N> t0 = (-B-Q)*rcp_2A;
        const vfloat<N> t1 = (-B+Q)*rcp_2A;
        
        /* calculates u and Ng for near hit */
        {
          u0_o = (Oz+t0*dOz)*rl;
          const Vec3vfN Pr = t0*Vec3vfN(dir);
          const Vec3vfN Pl = v0 + u0_o*(v1-v0);
          Ng0_o = Pr-Pl;
        }
        
        /* calculates u and Ng for far hit */
        {
          u1_o = (Oz+t1*dOz)*rl;
          const Vec3vfN Pr = t1*Vec3vfN(dir);
          const Vec3vfN Pl = v0 + u1_o*(v1-v0);
          Ng1_o = Pr-Pl;
        }

        t_o.lower = select(valid, t0, vfloat<N>(pos_inf));
        t_o.upper = select(valid, t1, vfloat<N>(neg_inf));

        /* special case for rays that are parallel to the cylinder */
        const vfloat<N> eps = 16.0f*float(ulp)*max(abs(dOdO),abs(sqr(dOz)));
        vbool<N> validt = valid & (abs(A) < eps); 
        if (unlikely(any(validt))) 
        {
          vbool<N> inside = C <= 0.0f;
          t_o.lower = select(validt,select(inside,vfloat<N>(neg_inf),vfloat<N>(pos_inf)),t_o.lower);
          t_o.upper = select(validt,select(inside,vfloat<N>(pos_inf),vfloat<N>(neg_inf)),t_o.upper);
          valid &= inside;
        }
        return valid;
      }

      __forceinline vbool<N> intersect(const Vec3fa& org_i, const Vec3fa& dir, BBox<vfloat<N>>& t_o) const
      {
        vfloat<N> u0_o; Vec3vfN Ng0_o;
        vfloat<N> u1_o; Vec3vfN Ng1_o;
        return intersect(org_i,dir,t_o,u0_o,Ng0_o,u1_o,Ng1_o);
      }
    };
  }
}

