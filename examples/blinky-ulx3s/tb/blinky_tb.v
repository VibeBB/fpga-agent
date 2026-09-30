// SPDX-License-Identifier: BSD-3-Clause
`timescale 1ns / 1ps
module blinky_tb;
  reg clk = 1'b0;
  wire [7:0] led;
  integer i;

  blinky #(.WIDTH(10)) dut (.clk_25mhz(clk), .led(led));

  always #20 clk = ~clk;

  initial begin
    for (i = 0; i < 8; i = i + 1) begin
      if (led !== i[7:0]) $fatal(1, "FAIL: led=%0d expected %0d", led, i);
      repeat (4) @(posedge clk);
      #1;
    end
    $display("PASS: blinky counts");
    $finish;
  end
endmodule
