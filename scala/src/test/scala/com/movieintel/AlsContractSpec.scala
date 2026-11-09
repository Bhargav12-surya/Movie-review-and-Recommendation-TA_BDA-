package com.movieintel

import com.movieintel.recommendation.AlsParameters
import org.scalatest.funsuite.AnyFunSuite

class AlsContractSpec extends AnyFunSuite {
  test("ALS parameter ranges reject nonfinite regularization and unbounded local work") {
    assertThrows[IllegalArgumentException](AlsParameters(regularization = Double.NaN))
    assertThrows[IllegalArgumentException](AlsParameters(rank = 0))
    assertThrows[IllegalArgumentException](AlsParameters(iterations = 31))
    assertThrows[IllegalArgumentException](AlsParameters(blocks = 8))
    assert(AlsParameters().rank == 32)
  }
}
