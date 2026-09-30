// SPDX-License-Identifier: BSD-3-Clause
`timescale 1ns / 1ps
module blinky_tb;
  reg clk = 1'b0;
  wire [5:0] led_n;
  integer i;

  blinky #(.WIDTH(8)) dut (.clk(clk), .led_n(led_n));

  always #18.5 clk = ~clk;

  initial begin
    #1;
    for (i = 0; i < 8; i = i + 1) begin
      if (~led_n !== i[5:0]) $fatal(1, "FAIL: led_n=%b expected count %0d", led_n, i);
      repeat (4) @(posedge clk);
      #1;
    end
    $display("PASS: blinky counts");
    $finish;
  end
endmodule
