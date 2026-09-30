-- SPDX-License-Identifier: BSD-3-Clause
library ieee;
  use ieee.std_logic_1164.all;

entity uart_echo_tb is
end entity uart_echo_tb;

architecture sim of uart_echo_tb is

  constant c_CLK_HZ : positive := 12_000_000;
  constant c_BAUD   : positive := 1_000_000;
  constant c_CLK    : time     := 1 sec / c_CLK_HZ;
  constant c_BIT    : time     := (c_CLK_HZ / c_BAUD) * c_CLK;
  constant c_BYTE   : std_logic_vector(7 downto 0) := x"41";

  signal clk    : std_logic := '0';
  signal rx     : std_logic := '1';
  signal tx     : std_logic;
  signal ledr_n : std_logic;
  signal done   : boolean   := false;

begin

  clk <= not clk after c_CLK / 2 when not done;

  dut : entity work.uart_echo
    generic map (
      g_CLK_HZ => c_CLK_HZ,
      g_BAUD   => c_BAUD
    )
    port map (
      clk    => clk,
      rx     => rx,
      tx     => tx,
      ledr_n => ledr_n
    );

  stimulus : process is
  begin
    wait for 20 * c_BIT;
    rx <= '0';
    wait for c_BIT;
    for i in 0 to 7 loop
      rx <= c_BYTE(i);
      wait for c_BIT;
    end loop;
    rx <= '1';
    wait;
  end process stimulus;

  check : process is
    variable byte : std_logic_vector(7 downto 0);
  begin
    wait until tx = '1';
    wait until tx = '0' for 100 us;
    assert tx = '0'
      report "no start bit echoed on tx"
      severity failure;
    wait for c_BIT + c_BIT / 2;
    for i in 0 to 7 loop
      byte(i) := tx;
      wait for c_BIT;
    end loop;
    assert tx = '1'
      report "missing stop bit"
      severity failure;
    assert byte = c_BYTE
      report "echo mismatch: 0x" & to_hstring(byte)
      severity failure;
    assert ledr_n = '0'
      report "activity LED is not lit"
      severity failure;
    report "PASS: echoed 0x" & to_hstring(byte);
    done <= true;
    wait;
  end process check;

end architecture sim;
