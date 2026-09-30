-- SPDX-License-Identifier: BSD-3-Clause
-- Echoes every byte received on `rx` back on `tx` using the Colibri UART,
-- and flashes the active-low red LED on each received byte. The UART
-- receiver's one-cycle `rx_valid` is held in a one-byte buffer until the
-- transmitter's ready/valid handshake accepts it.
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

library colibri;

entity uart_echo is
  generic (
    g_CLK_HZ : positive := 12_000_000;
    g_BAUD   : positive := 115_200
  );
  port (
    clk    : in    std_logic;
    rx     : in    std_logic;
    tx     : out   std_logic;
    ledr_n : out   std_logic
  );
end entity uart_echo;

architecture rtl of uart_echo is

  signal por_count : unsigned(3 downto 0) := (others => '0');
  signal reset     : std_logic;
  signal rx_data   : std_logic_vector(7 downto 0);
  signal rx_valid  : std_logic;
  signal tx_data   : std_logic_vector(7 downto 0) := (others => '0');
  signal tx_valid  : std_logic := '0';
  signal tx_ready  : std_logic;
  signal seen      : std_logic;

begin

  reset <= '0' when por_count = 15 else '1';

  process (clk) is
  begin
    if rising_edge(clk) then
      if reset = '1' then
        por_count <= por_count + 1;
        tx_valid  <= '0';
      elsif rx_valid = '1' then
        tx_data  <= rx_data;
        tx_valid <= '1';
      elsif tx_ready = '1' then
        tx_valid <= '0';
      end if;
    end if;
  end process;

  u_uart : entity colibri.uart
    generic map (
      g_CLOCK_PERIOD => 1 sec / g_CLK_HZ,
      g_BAUD_RATE    => g_BAUD
    )
    port map (
      clk_i      => clk,
      reset_i    => reset,
      tx_data_i  => tx_data,
      tx_valid_i => tx_valid,
      tx_ready_o => tx_ready,
      rx_data_o  => rx_data,
      rx_valid_o => rx_valid,
      rx_pin_i   => rx,
      tx_pin_o   => tx
    );

  u_led : entity work.pulse_stretch
    generic map (
      g_CYCLES => g_CLK_HZ / 20
    )
    port map (
      clk     => clk,
      trigger => rx_valid,
      active  => seen
    );

  ledr_n <= not seen;

end architecture rtl;
